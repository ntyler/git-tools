"""Build compact Git diff context for OpenAI prompts."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MAX_DIFF_CHARS = 60000
MAX_DIFF_CHARS_ENV = "GIT_TOOLS_MAX_DIFF_CHARS"
MIN_FILE_DIFF_CHARS = 1200
TRUNCATION_MARGIN = 500


@dataclass(frozen=True)
class DiffContext:
    """Prompt-ready staged change context."""

    text: str
    truncated: bool
    original_diff_chars: int
    context_chars: int


def get_max_diff_chars() -> int:
    """Read the diff context limit from the environment."""
    raw_value = os.getenv(MAX_DIFF_CHARS_ENV)

    if not raw_value:
        return DEFAULT_MAX_DIFF_CHARS

    try:
        value = int(raw_value)
    except ValueError:
        print(
            f"Ignoring invalid {MAX_DIFF_CHARS_ENV}={raw_value!r}; "
            f"using {DEFAULT_MAX_DIFF_CHARS}."
        )
        return DEFAULT_MAX_DIFF_CHARS

    if value < 5000:
        print(
            f"Ignoring {MAX_DIFF_CHARS_ENV}={value}; use at least 5000 "
            f"characters."
        )
        return DEFAULT_MAX_DIFF_CHARS

    return value


def build_staged_diff_context(
    *,
    diff: str,
    name_status: str = "",
    stat: str = "",
    max_chars: int | None = None,
) -> DiffContext:
    """Return prompt-ready context while keeping huge diffs under a cap."""
    limit = max_chars if max_chars is not None else get_max_diff_chars()
    original_diff_chars = len(diff)
    compact_diff, truncated = compact_unified_diff(
        diff,
        max(1000, limit - _metadata_chars(name_status, stat) - TRUNCATION_MARGIN),
    )

    sections = []
    if name_status:
        sections.append(_fenced_section("Changed files", "text", name_status))

    if stat:
        sections.append(_fenced_section("Diff stats", "text", stat))

    if truncated:
        sections.append(
            "Note: The staged diff excerpt below was shortened to stay within "
            "OpenAI token and rate limits. The file list and stats above still "
            "cover the staged changes."
        )

    sections.append(_fenced_section("Staged diff excerpt", "diff", compact_diff))
    text = "\n\n".join(sections)

    if len(text) > limit:
        text = _truncate_text(
            text,
            limit,
            "additional staged diff context omitted to fit the configured limit",
        )
        truncated = True

    return DiffContext(
        text=text,
        truncated=truncated,
        original_diff_chars=original_diff_chars,
        context_chars=len(text),
    )


def compact_unified_diff(diff: str, max_chars: int) -> tuple[str, bool]:
    """Keep representative per-file diff excerpts within max_chars."""
    if len(diff) <= max_chars:
        return diff, False

    chunks = _split_diff_by_file(diff)
    if not chunks:
        return _truncate_text(diff, max_chars, "staged diff omitted"), True

    pieces: list[str] = []
    truncated = False
    remaining = max_chars

    for index, chunk in enumerate(chunks):
        files_left = len(chunks) - index
        separator_chars = 1 if pieces else 0
        usable_remaining = remaining - separator_chars

        if usable_remaining < max(400, MIN_FILE_DIFF_CHARS // 2):
            omitted_count = len(chunks) - index
            pieces.append(f"...[{omitted_count} file diff(s) omitted]...")
            truncated = True
            break

        budget = min(
            usable_remaining,
            max(MIN_FILE_DIFF_CHARS, usable_remaining // files_left),
        )

        if len(chunk) <= budget:
            piece = chunk
        else:
            piece = _truncate_text(chunk, budget, "file diff omitted")
            truncated = True

        pieces.append(piece)
        remaining -= len(piece) + separator_chars

    compacted = "\n".join(pieces)
    if len(compacted) > max_chars:
        compacted = _truncate_text(compacted, max_chars, "staged diff omitted")
        truncated = True

    return compacted, truncated


def _split_diff_by_file(diff: str) -> list[str]:
    chunks: list[list[str]] = []
    current: list[str] = []

    for line in diff.splitlines():
        if line.startswith("diff --git ") and current:
            chunks.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        chunks.append(current)

    return ["\n".join(chunk) for chunk in chunks]


def _truncate_text(text: str, max_chars: int, reason: str) -> str:
    omitted_chars = len(text) - max_chars
    marker = f"\n...[{omitted_chars:,} characters {reason}]...\n"

    if max_chars <= len(marker) + 20:
        return text[:max_chars]

    while True:
        marker = f"\n...[{omitted_chars:,} characters {reason}]...\n"
        head_chars = max_chars - len(marker)
        next_omitted_chars = len(text) - head_chars
        if next_omitted_chars == omitted_chars:
            break
        omitted_chars = next_omitted_chars

    head_chars = max_chars - len(marker)
    return text[:head_chars].rstrip() + marker.rstrip()


def _metadata_chars(name_status: str, stat: str) -> int:
    return len(name_status) + len(stat) + 200


def _fenced_section(title: str, language: str, content: str) -> str:
    return f"{title}:\n```{language}\n{content}\n```"
