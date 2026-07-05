import html
import re

from telegram import Message
from telegram.constants import ParseMode

RAW_CHUNK_LIMIT = 2800


async def reply_markdown(message: Message, text: str) -> None:
    for chunk in split_markdown(text):
        await message.reply_text(
            markdown_to_html(chunk),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )


def split_markdown(text: str) -> list[str]:
    blocks = _markdown_blocks(_close_open_fence(text.strip()))
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= RAW_CHUNK_LIMIT:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = block
    if current:
        chunks.append(current)
    return chunks or [""]


def markdown_to_html(text: str) -> str:
    protected, code_blocks = _protect_code(_close_open_fence(text))
    escaped = html.escape(protected)
    lines = [_format_line(line) for line in escaped.splitlines()]
    formatted = "\n".join(lines)
    formatted = _format_inline(formatted)
    return _restore_code(formatted, code_blocks)


def _protect_code(text: str) -> tuple[str, list[tuple[str, str]]]:
    blocks: list[tuple[str, str]] = []

    def store_block(match: re.Match[str]) -> str:
        token = f"AIRA_CODE_BLOCK_{len(blocks)}_TOKEN"
        language = re.sub(r"[^a-zA-Z0-9_+#.-]", "", match.group(1).strip())
        code = html.escape(match.group(2).strip())
        rendered = (
            f'<pre><code class="language-{language}">{code}</code></pre>'
            if language
            else f"<pre>{code}</pre>"
        )
        blocks.append((token, rendered))
        return token

    protected = re.sub(r"```([^\n`]*)\n?(.*?)```", store_block, text, flags=re.DOTALL)

    def store_inline(match: re.Match[str]) -> str:
        token = f"AIRA_INLINE_CODE_{len(blocks)}_TOKEN"
        blocks.append((token, f"<code>{html.escape(match.group(1))}</code>"))
        return token

    return re.sub(r"`([^`\n]+)`", store_inline, protected), blocks


def _format_line(line: str) -> str:
    heading = re.match(r"^\s*#{1,6}\s+(.+)$", line)
    if heading:
        return f"<b>{heading.group(1)}</b>"
    if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
        return "──────────"
    line = re.sub(r"^\s*[-+*]\s+", "• ", line)
    line = re.sub(r"^\s*&gt;\s?", "▌ ", line)
    if line.count("|") >= 2:
        return f"<code>{line}</code>"
    return line


def _format_inline(text: str) -> str:
    text = re.sub(
        r"\[([^\]]+)]\((https?://[^)\s]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _restore_code(text: str, blocks: list[tuple[str, str]]) -> str:
    for token, replacement in blocks:
        text = text.replace(token, replacement)
    return text


def _markdown_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```[^\n`]*\n?.*?```", re.DOTALL)
    blocks: list[str] = []
    position = 0
    for match in pattern.finditer(text):
        blocks.extend(_text_blocks(text[position : match.start()]))
        blocks.extend(_code_blocks(match.group(0)))
        position = match.end()
    blocks.extend(_text_blocks(text[position:]))
    return [block for block in blocks if block]


def _text_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for paragraph in re.split(r"\n{2,}", text.strip()):
        blocks.extend(_split_by_lines(paragraph, RAW_CHUNK_LIMIT))
    return blocks


def _code_blocks(block: str) -> list[str]:
    match = re.fullmatch(r"```([^\n`]*)\n?(.*?)```", block, re.DOTALL)
    if match is None:
        return _split_by_lines(block, RAW_CHUNK_LIMIT)
    language, code = match.group(1).strip(), match.group(2).strip()
    content_limit = RAW_CHUNK_LIMIT - len(language) - 10
    parts = _split_by_lines(code, content_limit)
    return [f"```{language}\n{part}\n```" for part in parts]


def _split_by_lines(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text] if text else []
    parts: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                parts.append(current.rstrip())
                current = ""
            parts.extend(line[index : index + limit] for index in range(0, len(line), limit))
        elif len(current) + len(line) > limit:
            parts.append(current.rstrip())
            current = line
        else:
            current += line
    if current:
        parts.append(current.rstrip())
    return parts


def _close_open_fence(text: str) -> str:
    return f"{text}\n```" if text.count("```") % 2 else text
