"""Generate an OpenAI-powered pull request title and description."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


DEFAULT_MODEL = "gpt-4o-mini"
LOCAL_API_KEY_ENV = "OPENAI_API_KEY_git_tools_local"
STANDARD_API_KEY_ENV = "OPENAI_API_KEY"


def run_git_command(args: list[str], allow_failure: bool = False) -> str:
    """Run a Git command from the current working directory."""
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

    if result.returncode != 0 and not allow_failure:
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
        f"Set {LOCAL_API_KEY_ENV} or {STANDARD_API_KEY_ENV}, then try again."
    )
    return False


def collect_pr_context() -> tuple[str, str]:
    """Use staged changes first, then fall back to recent commits."""
    staged_diff = run_git_command(["diff", "--staged"]).strip()
    if staged_diff:
        return "staged diff", staged_diff

    recent_commits = run_git_command(
        ["log", "--oneline", "--decorate", "-n", "10"],
        allow_failure=True,
    ).strip()
    if recent_commits:
        return "recent commits", recent_commits

    return "", ""


def load_prompt() -> str:
    """Load the reusable PR prompt from this repo."""
    repo_root = Path(__file__).resolve().parents[1]
    prompt_path = repo_root / "prompts" / "pr_prompt.txt"

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    return "Generate a pull request title and description from the provided changes."


def generate_pr_description(context_name: str, content: str) -> str:
    """Send staged changes or recent commits to OpenAI."""
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
                        "Create a pull request title and description from this "
                        f"{context_name}:\n\n```text\n{content}\n```"
                    ),
                },
            ],
        )
    except OpenAIError as error:
        raise RuntimeError(f"OpenAI API error: {error}") from error

    return (response.choices[0].message.content or "").strip()


def main() -> int:
    context_name, content = collect_pr_context()

    if not content:
        print("No staged changes or recent commits found for a pull request summary.")
        return 0

    if not configure_openai_api_key():
        return 1

    try:
        output = generate_pr_description(context_name, content)
    except RuntimeError as error:
        print(error)
        return 1
    except Exception as error:
        print(f"Unexpected error while generating the PR description: {error}")
        return 1

    if not output:
        print("OpenAI returned an empty response. Please try again.")
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
