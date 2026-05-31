# Sample Output

## Commit Message

```text
Summary:
feat: add OpenAI commit message generator

Description:
- Add a reusable script for generating commit messages from staged diffs
- Use OpenAI to produce conventional commit summaries and bullet descriptions
- Copy generated messages to the clipboard when pyperclip is available
```

## Pull Request Description

```markdown
Title:
Add reusable Git workflow utilities

Description:
## Summary
- Add starter scripts for commit messages, PR descriptions, and diff summaries
- Add reusable prompts for OpenAI-powered Git workflow automation
- Document setup, environment variables, and Windows-friendly usage

## Testing
- Not run; example output only
```

## Diff Summary

```text
- Changed files:
  - README.md: documents install, API key setup, and script usage
  - git/generate_commit_message.py: adds staged diff commit generation
  - prompts/commit_prompt.txt: adds reusable commit prompt instructions
- User-visible impact:
  - Developers can generate commit messages from any Git repository
  - Output is printed in the terminal and copied to the clipboard when available
```
