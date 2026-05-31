"""Summarize staged Git changes and user-visible impact."""

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
        f"Set {LOCAL_API_KEY_ENV} or {STANDARD_API_KEY_ENV}, then try again."
    )
    return False


def summarize_diff(name_status: str, diff: str) -> str:
    """Ask OpenAI for a practical summary of staged changes."""
    try:
        from openai import OpenAI, OpenAIError
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI SDK is not installed. Run python -m pip install -r requirements.txt."
        ) from error

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize staged Git changes for a developer. "
                        "Focus on changed files and user-visible impact. "
                        "Use concise bullet points."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Changed files:\n"
                        f"```text\n{name_status}\n```\n\n"
                        "Staged diff:\n"
                        f"```diff\n{diff}\n```"
                    ),
                },
            ],
        )
    except OpenAIError as error:
        raise RuntimeError(f"OpenAI API error: {error}") from error

    return (response.choices[0].message.content or "").strip()


def main() -> int:
    staged_diff = run_git_command(["diff", "--staged"]).strip()

    if not staged_diff:
        print("No staged changes found. Stage files with git add, then try again.")
        return 0

    if not configure_openai_api_key():
        return 1

    name_status = run_git_command(["diff", "--staged", "--name-status"]).strip()

    try:
        output = summarize_diff(name_status, staged_diff)
    except RuntimeError as error:
        print(error)
        return 1
    except Exception as error:
        print(f"Unexpected error while summarizing the diff: {error}")
        return 1

    if not output:
        print("OpenAI returned an empty response. Please try again.")
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
