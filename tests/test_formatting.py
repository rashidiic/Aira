from src.handlers.formatting import markdown_to_html, split_markdown


def test_markdown_is_converted_to_telegram_html() -> None:
    source = "## Заголовок\n\n**Важно** и `код`\n\n- Первый\n- Второй"

    result = markdown_to_html(source)

    assert "<b>Заголовок</b>" in result
    assert "<b>Важно</b>" in result
    assert "<code>код</code>" in result
    assert "• Первый" in result


def test_html_from_model_is_escaped() -> None:
    result = markdown_to_html("<script>alert('x')</script>")

    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_long_answer_is_split() -> None:
    chunks = split_markdown("a" * 6000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2800 for chunk in chunks)


def test_long_csharp_block_stays_valid_after_split() -> None:
    source = "```csharp\n" + "Console.WriteLine(1);\n" * 300 + "```"

    chunks = split_markdown(source)
    rendered = [markdown_to_html(chunk) for chunk in chunks]

    assert len(chunks) > 1
    assert all(chunk.startswith("```csharp\n") and chunk.endswith("\n```") for chunk in chunks)
    assert all('<pre><code class="language-csharp">' in item for item in rendered)
    assert all("```" not in item for item in rendered)


def test_unclosed_code_fence_is_repaired() -> None:
    result = markdown_to_html("```csharp\nvar value = 1;")

    assert '<pre><code class="language-csharp">' in result
    assert "```" not in result
