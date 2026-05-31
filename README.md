# git-tools

Reusable personal developer utilities for Git workflows, OpenAI-powered commit
message generation, pull request summaries, diff summaries, repository analysis,
and workflow automation.

This repo is designed to live in one place, such as `D:\GitHub\git-tools`, while
the scripts are run from any other Git repository you are working in.

## Install

From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

You can also install the requirements into your normal Python environment:

```powershell
python -m pip install -r requirements.txt
```

## Set Your OpenAI API Key

Do not store API keys in this repository or commit them to Git.

This repo supports a local key environment variable named
`OPENAI_API_KEY_git_tools_local`, and it also supports the standard
`OPENAI_API_KEY` variable.

For the current PowerShell session:

```powershell
$env:OPENAI_API_KEY_git_tools_local = "your_api_key_here"
```

Or, using the standard OpenAI SDK variable:

```powershell
$env:OPENAI_API_KEY = "your_api_key_here"
```

To persist the local key for future PowerShell sessions:

```powershell
setx OPENAI_API_KEY_git_tools_local "your_api_key_here"
```

Open a new terminal after running `setx` so the new environment variable is
available.

Optional: set a different OpenAI model with:

```powershell
$env:OPENAI_MODEL = "gpt-4o-mini"
```

## Generate a Commit Message From Any Git Repo

1. Open a terminal in the Git repository where you are making changes.
2. Stage the files you want included in the commit.
3. Run the commit message generator from this repo.

Example:

```powershell
git add README.md git\generate_commit_message.py
python D:\GitHub\git-tools\git\generate_commit_message.py
```

The script runs `git diff --staged` in your current working directory, sends the
staged diff to OpenAI, prints a conventional commit style message, and copies the
result to your clipboard when `pyperclip` is available.

To stage all current changes before generating the message:

```powershell
python D:\GitHub\git-tools\git\generate_commit_message.py --stage-all
```

To generate the message and create a Git commit using the generated Summary and
Description:

```powershell
python D:\GitHub\git-tools\git\generate_commit_message.py --stage-all --commit
```

The commit command asks for confirmation before creating the commit. After a
successful commit, it also asks whether you want to push the commit to the
configured remote.

To skip the commit confirmation prompt:

```powershell
python D:\GitHub\git-tools\git\generate_commit_message.py --stage-all --commit --yes
```

The push prompt still asks before running `git push`.

## Other Tools

Generate a starter pull request title and description:

```powershell
python D:\GitHub\git-tools\git\generate_pr_description.py
```

Summarize staged changes and user-visible impact:

```powershell
python D:\GitHub\git-tools\git\summarize_diff.py
```

## Example Output

```text
Summary:
feat: add OpenAI commit message generator

Description:
- Add a reusable script for staged Git diffs
- Generate conventional commit summaries with OpenAI
- Copy generated output to the clipboard when available
- Document setup and usage for Windows-friendly workflows
```

See [examples/sample_output.md](examples/sample_output.md) for more examples.
