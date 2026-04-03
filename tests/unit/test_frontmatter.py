"""Tests for frontmatter parser using fixture markdown files."""

from pathlib import Path

import pytest

from bullish_ssg.content.frontmatter import FrontmatterParseError, FrontmatterParser, parse_frontmatter


def test_parse_valid_frontmatter(fixture_file: callable) -> None:
    vault_path = fixture_file("frontmatter")
    parser = FrontmatterParser(vault_path)

    parsed = parser.parse(fixture_file("frontmatter/valid.md"))

    assert parsed.relative_path == Path("valid.md")
    assert parsed.title == "Valid Title"
    assert parsed.slug == "valid-title"
    assert parsed.content_type == "doc"
    assert "Body content." in parsed.content


def test_parse_without_frontmatter(fixture_file: callable) -> None:
    vault_path = fixture_file("frontmatter")
    parser = FrontmatterParser(vault_path)

    parsed = parser.parse(fixture_file("frontmatter/no_frontmatter.md"))

    assert parsed.relative_path == Path("no_frontmatter.md")
    assert parsed.metadata == {}
    assert "Plain content" in parsed.content


def test_parse_invalid_frontmatter_raises(fixture_file: callable) -> None:
    vault_path = fixture_file("frontmatter")
    parser = FrontmatterParser(vault_path)

    with pytest.raises(FrontmatterParseError):
        parser.parse(fixture_file("frontmatter/invalid_yaml.md"))


def test_parse_safe_returns_defaults_on_error(fixture_file: callable) -> None:
    vault_path = fixture_file("frontmatter")
    parser = FrontmatterParser(vault_path)

    parsed = parser.parse_safe(fixture_file("frontmatter/invalid_yaml.md"), default_metadata={"publish": False})

    assert parsed.metadata == {"publish": False}
    assert parsed.content == ""


def test_parse_batch_collects_successes_and_failures(fixture_file: callable) -> None:
    vault_path = fixture_file("frontmatter")
    parser = FrontmatterParser(vault_path)

    successes, failures = parser.parse_batch(
        [
            fixture_file("frontmatter/valid.md"),
            fixture_file("frontmatter/invalid_yaml.md"),
            fixture_file("frontmatter/no_frontmatter.md"),
        ]
    )

    assert len(successes) == 2
    assert len(failures) == 1


def test_convenience_parse_frontmatter(fixture_file: callable) -> None:
    parsed = parse_frontmatter(
        fixture_file("frontmatter/valid.md"),
        vault_path=fixture_file("frontmatter"),
    )
    assert parsed.title == "Valid Title"
