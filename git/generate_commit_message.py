"""Generate an OpenAI-powered commit message from staged Git changes."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_MODEL = "gpt-4o-mini"
LOCAL_API_KEY_ENV = "OPENAI_API_KEY_git_tools_local"
STANDARD_API_KEY_ENV = "OPENAI_API_KEY"


def run_git_command(args: list[str]) -> str:
    """Run a Git command in the current working directory and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        print("Git was not found. Install Git and make sure it is on your PATH.")
        sys.exit(1)

    if result.returncode != 0:
        message = result.stderr.strip() or "Git command failed."
        print(f"Unable to run git {' '.join(args)}:\n{message}")
        sys.exit(1)

    return result.stdout


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line options for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a commit message from the current Git repository."
    )
    parser.add_argument(
        "--stage-all",
        action="store_true",
        help="Run git add -A before generating the commit message.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create a Git commit using the generated Summary and Description.",
    )
    parser.add_argument(
        "--create-commit",
        choices=["ask", "yes", "no"],
        default="ask",
        help=(
            "When used with --commit, choose whether to create the commit: "
            "ask, yes, or no."
        ),
    )
    parser.add_argument(
        "--push-committed-changes",
        choices=["ask", "yes", "no"],
        default="ask",
        help=(
            "After a commit is created, choose whether to run git push: "
            "ask, yes, or no."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Shortcut for --create-commit yes when used with --commit.",
    )
    return parser


def configure_openai_api_key() -> bool:
    """Prefer the local key variable, but support the standard OpenAI variable."""
    local_key = os.getenv(LOCAL_API_KEY_ENV)
    standard_key = os.getenv(STANDARD_API_KEY_ENV)

    if local_key:
        os.environ[STANDARD_API_KEY_ENV] = local_key
        return True

    if standard_key:
        return True

    print(
        "OpenAI API key not found.\n"
        f"Set {LOCAL_API_KEY_ENV} or {STANDARD_API_KEY_ENV}, then try again.\n"
        f'PowerShell example: $env:{LOCAL_API_KEY_ENV} = "your_api_key_here"'
    )
    return False


def load_prompt() -> str:
    """Load the reusable commit prompt from this repo."""
    repo_root = Path(__file__).resolve().parents[1]
    prompt_path = repo_root / "prompts" / "commit_prompt.txt"

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    return (
        "Generate a conventional commit message from the staged diff. "
        "Return exactly a Summary and Description."
    )


def generate_commit_message(diff: str) -> str:
    """Send the staged diff to OpenAI and return the generated commit text."""
    try:
        from openai import OpenAI, OpenAIError
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Run python -m pip install -r requirements.txt."
        ) from error

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    prompt = load_prompt()

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "Create a commit message for this staged diff:\n\n"
                        f"```diff\n{diff}\n```"
                    ),
                },
            ],
        )
    except OpenAIError as error:
        raise RuntimeError(f"OpenAI API error: {error}") from error

    return (response.choices[0].message.content or "").strip()


def parse_commit_output(output: str) -> tuple[str, str]:
    """Extract Summary and Description sections from the generated output."""
    summary_lines: list[str] = []
    description_lines: list[str] = []
    active_section: str | None = None

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        normalized = line.strip().lower()

        if normalized.startswith("summary:"):
            active_section = "summary"
            inline_value = line.split(":", 1)[1].strip()
            if inline_value:
                summary_lines.append(inline_value)
            continue

        if normalized.startswith("description:"):
            active_section = "description"
            inline_value = line.split(":", 1)[1].strip()
            if inline_value:
                description_lines.append(inline_value)
            continue

        if active_section == "summary" and line.strip():
            summary_lines.append(line.strip())
        elif active_section == "description":
            description_lines.append(line)

    summary = " ".join(summary_lines).strip()
    description = "\n".join(description_lines).strip()

    if not summary:
        raise RuntimeError("Could not find a Summary section in the generated output.")

    if not description:
        raise RuntimeError("Could not find a Description section in the generated output.")

    return summary, description


def confirm_commit(summary: str, description: str) -> bool:
    """Ask before creating a commit unless the user passed --yes."""
    print("\nCommit to create:")
    print(f"\nSummary:\n{summary}")
    print(f"\nDescription:\n{description}")
    answer = input("\nCreate this commit? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def create_commit(summary: str, description: str) -> None:
    """Create the Git commit using Summary as subject and Description as body."""
    run_git_command(["commit", "-m", summary, "-m", description])
    print("\nCreated Git commit with the generated message.")


def confirm_push() -> bool:
    """Ask whether to push after a successful commit."""
    answer = input("\nPush this commit to the remote? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def should_create_commit(
    args: argparse.Namespace,
    summary: str,
    description: str,
) -> bool:
    """Choose whether to create the commit from flags or an interactive prompt."""
    if args.yes:
        return True

    if args.create_commit == "yes":
        return True

    if args.create_commit == "no":
        return False

    return confirm_commit(summary, description)


def should_push_committed_changes(args: argparse.Namespace) -> bool:
    """Choose whether to push from flags or an interactive prompt."""
    if args.push_committed_changes == "yes":
        return True

    if args.push_committed_changes == "no":
        return False

    return confirm_push()


def push_changes() -> bool:
    """Push the current branch to its configured remote."""
    try:
        result = subprocess.run(
            ["git", "push"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        print("Git was not found. Install Git and make sure it is on your PATH.")
        return False

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        print(stdout)

    if result.returncode != 0:
        print("\nCommit was created, but git push failed.")
        if stderr:
            print(stderr)
        return False

    if stderr:
        print(stderr)

    print("\nPushed committed changes.")
    return True


def copy_to_clipboard(text: str) -> None:
    """Copy text to the clipboard when pyperclip is installed and working."""
    try:
        import pyperclip

        pyperclip.copy(text)
        print("\nCopied commit message to clipboard.")
    except Exception:
        print("\nCould not copy to clipboard, but the output is printed above.")


def main() -> int:
    args = build_parser().parse_args()

    if args.stage_all:
        run_git_command(["add", "-A"])
        print("Staged all changes with git add -A.")

    staged_diff = run_git_command(["diff", "--staged"]).strip()

    if not staged_diff:
        print("No staged changes found. Stage files with git add, then try again.")
        return 0

    if not configure_openai_api_key():
        return 1

    try:
        output = generate_commit_message(staged_diff)
    except RuntimeError as error:
        print(error)
        return 1
    except Exception as error:
        print(f"Unexpected error while generating the commit message: {error}")
        return 1

    if not output:
        print("OpenAI returned an empty response. Please try again.")
        return 1

    print(output)
    copy_to_clipboard(output)

    if args.commit:
        try:
            summary, description = parse_commit_output(output)
        except RuntimeError as error:
            print(error)
            return 1

        if should_create_commit(args, summary, description):
            create_commit(summary, description)
            if should_push_committed_changes(args) and not push_changes():
                return 1
        else:
            print("\nCommit canceled. Your changes are still staged.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
