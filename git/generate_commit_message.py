"""Generate an OpenAI-powered commit message from staged Git changes."""

from __future__ import annotations

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


def copy_to_clipboard(text: str) -> None:
    """Copy text to the clipboard when pyperclip is installed and working."""
    try:
        import pyperclip

        pyperclip.copy(text)
        print("\nCopied commit message to clipboard.")
    except Exception:
        print("\nCould not copy to clipboard, but the output is printed above.")


def main() -> int:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
