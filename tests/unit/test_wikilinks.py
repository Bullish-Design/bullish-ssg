"""Tests for wikilink parsing and resolution using fixture data."""

from pathlib import Path

import pytest

from bullish_ssg.validate.wikilinks import (
    HeadingExtractor,
    PageIndex,
    ParsedWikilink,
    WikilinkDiagnostic,
    WikilinkParser,
    WikilinkResolver,
    build_page_index,
)


@pytest.fixture
def wikilink_fixture_path(fixture_file: callable) -> Path:
    return fixture_file("wikilinks")


class TestWikilinkParser:
    """Tests for wikilink parsing."""

    def test_parse_basic_wikilink(self) -> None:
        parser = WikilinkParser()
        content = "Check out [[getting-started]] for more info."
        links = list(parser.parse(content))

        assert len(links) == 1
        assert links[0].page == "getting-started"
        assert links[0].alias is None
        assert links[0].heading is None
        assert links[0].block_id is None
        assert links[0].line_number == 1

    def test_parse_aliased_wikilink(self) -> None:
        parser = WikilinkParser()
        content = "See [[about|About Us]] for details."
        links = list(parser.parse(content))

        assert len(links) == 1
        assert links[0].page == "about"
        assert links[0].alias == "About Us"

    def test_parse_heading_anchor(self) -> None:
        parser = WikilinkParser()
        content = "Jump to [[getting-started#installation]]."
        links = list(parser.parse(content))

        assert len(links) == 1
        assert links[0].page == "getting-started"
        assert links[0].heading == "installation"
        assert links[0].alias is None

    def test_parse_block_reference(self) -> None:
        parser = WikilinkParser()
        content = "Reference [[about#^block-id]] here."
        links = list(parser.parse(content))

        assert len(links) == 1
        assert links[0].page == "about"
        assert links[0].block_id == "block-id"

    def test_parse_multiple_wikilinks(self) -> None:
        parser = WikilinkParser()
        content = "Link to [[page1]] and [[page2|alias]] and [[page3#heading]]."
        links = list(parser.parse(content))

        assert len(links) == 3
        assert links[0].page == "page1"
        assert links[1].page == "page2"
        assert links[2].page == "page3"

    def test_parse_wikilinks_with_line_numbers(self) -> None:
        parser = WikilinkParser()
        content = "First line\n[[link1]]\nThird line\n[[link2]]"
        links = list(parser.parse(content))

        assert len(links) == 2
        assert links[0].line_number == 2
        assert links[1].line_number == 4

    def test_parse_no_wikilinks(self) -> None:
        parser = WikilinkParser()
        content = "This has no wikilinks. Just regular text."
        links = list(parser.parse(content))

        assert len(links) == 0


class TestHeadingExtractor:
    """Tests for heading extraction."""

    def test_extract_headings(self) -> None:
        extractor = HeadingExtractor()
        content = """# Title

## Section 1

Some text.

### Subsection

## Section 2
"""
        headings = extractor.extract(content)

        assert headings == ["Title", "Section 1", "Subsection", "Section 2"]

    def test_normalize_heading(self) -> None:
        extractor = HeadingExtractor()
        assert extractor.normalize_heading("Hello World") == "hello-world"
        assert extractor.normalize_heading("Special!@#$%Chars") == "specialchars"
        assert extractor.normalize_heading("Multiple   Spaces") == "multiple-spaces"
        assert extractor.normalize_heading("-leading-trailing-") == "leading-trailing"

    def test_has_heading(self) -> None:
        extractor = HeadingExtractor()
        content = "# Getting Started\n\n## Installation\n\n### Details"

        assert extractor.has_heading(content, "Getting Started")
        assert extractor.has_heading(content, "Installation")
        assert extractor.has_heading(content, "Details")
        assert not extractor.has_heading(content, "Nonexistent")


class TestPageIndex:
    """Tests for page indexing."""

    def test_resolve_page_by_slug(self, tmp_path: Path) -> None:
        index = PageIndex(tmp_path)
        index.add_page(Path("getting-started.md"), ["getting-started"])
        index.add_page(Path("about.md"), ["about"])

        assert index.resolve_page("getting-started") == Path("getting-started.md")
        assert index.resolve_page("about") == Path("about.md")
        assert index.resolve_page("nonexistent") is None

    def test_resolve_page_case_insensitive(self, tmp_path: Path) -> None:
        index = PageIndex(tmp_path)
        index.add_page(Path("Getting-Started.md"), ["getting-started"])

        assert index.resolve_page("Getting-Started") == Path("Getting-Started.md")
        assert index.resolve_page("getting-started") == Path("Getting-Started.md")

    def test_build_page_index_from_files(self, wikilink_fixture_path: Path) -> None:
        content_files = [
            Path("index.md"),
            Path("getting-started.md"),
            Path("about.md"),
            Path("blog/post.md"),
        ]
        index = build_page_index(wikilink_fixture_path, content_files)

        assert index.resolve_page("index") == Path("index.md")
        assert index.resolve_page("getting-started") == Path("getting-started.md")
        assert index.resolve_page("about") == Path("about.md")
        assert index.resolve_page("post") == Path("blog/post.md")


class TestWikilinkResolver:
    """Tests for wikilink resolution and validation."""

    @pytest.fixture
    def populated_index(self, wikilink_fixture_path: Path) -> PageIndex:
        content_files = [
            Path("index.md"),
            Path("getting-started.md"),
            Path("about.md"),
            Path("features.md"),
            Path("blog/post.md"),
        ]
        return build_page_index(wikilink_fixture_path, content_files)

    @pytest.fixture
    def resolver(self, populated_index: PageIndex) -> WikilinkResolver:
        return WikilinkResolver(populated_index)

    def test_resolve_valid_page_link(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        link = ParsedWikilink(
            raw="[[getting-started]]",
            page="getting-started",
            alias=None,
            heading=None,
            block_id=None,
            line_number=5,
        )
        source = wikilink_fixture_path / "index.md"

        diagnostic = resolver.resolve(link, source)

        assert diagnostic is None

    def test_resolve_missing_page_fails(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        link = ParsedWikilink(
            raw="[[nonexistent]]",
            page="nonexistent",
            alias=None,
            heading=None,
            block_id=None,
            line_number=10,
        )
        source = wikilink_fixture_path / "about.md"

        diagnostic = resolver.resolve(link, source)

        assert diagnostic is not None
        assert diagnostic.severity == "error"
        assert "nonexistent" in diagnostic.reason
        assert diagnostic.line_number == 10

    def test_resolve_valid_heading(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        link = ParsedWikilink(
            raw="[[getting-started#installation]]",
            page="getting-started",
            alias=None,
            heading="installation",
            block_id=None,
            line_number=3,
        )
        source = wikilink_fixture_path / "blog/post.md"

        diagnostic = resolver.resolve(link, source)

        assert diagnostic is None

    def test_resolve_missing_heading_fails(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        link = ParsedWikilink(
            raw="[[getting-started#nonexistent]]",
            page="getting-started",
            alias=None,
            heading="nonexistent",
            block_id=None,
            line_number=3,
        )
        source = wikilink_fixture_path / "about.md"

        diagnostic = resolver.resolve(link, source)

        assert diagnostic is not None
        assert diagnostic.severity == "error"
        assert "Heading not found" in diagnostic.reason

    def test_block_reference_returns_warning(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        link = ParsedWikilink(
            raw="[[about#^block-id]]",
            page="about",
            alias=None,
            heading=None,
            block_id="block-id",
            line_number=7,
        )
        source = wikilink_fixture_path / "blog/post.md"

        diagnostic = resolver.resolve(link, source)

        assert diagnostic is not None
        assert diagnostic.severity == "warning"
        assert "Block reference validation not implemented" in diagnostic.reason

    def test_validate_file_finds_all_broken_links(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        about_file = wikilink_fixture_path / "about.md"
        diagnostics = resolver.validate_file(about_file)

        # Should find: missing page, missing heading
        errors = [d for d in diagnostics if d.severity == "error"]
        assert len(errors) == 2

        # Check for missing page error
        missing_page = [d for d in errors if "Page not found" in d.reason]
        assert len(missing_page) == 1
        assert "nonexistent" in missing_page[0].reason

        # Check for missing heading error
        missing_heading = [d for d in errors if "Heading not found" in d.reason]
        assert len(missing_heading) == 1
        assert "nonexistent-heading" in missing_heading[0].reason

    def test_validate_file_finds_block_warnings(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        post_file = wikilink_fixture_path / "blog/post.md"
        diagnostics = resolver.validate_file(post_file)

        warnings = [d for d in diagnostics if d.severity == "warning"]
        assert len(warnings) == 1
        assert "Block reference" in warnings[0].reason

    def test_validate_healthy_file_no_errors(
        self,
        resolver: WikilinkResolver,
        wikilink_fixture_path: Path,
    ) -> None:
        index_file = wikilink_fixture_path / "index.md"
        diagnostics = resolver.validate_file(index_file)

        assert len(diagnostics) == 0

    def test_unpublished_target_returns_warning(self, wikilink_fixture_path: Path) -> None:
        content_files = [Path("index.md"), Path("getting-started.md"), Path("about.md"), Path("features.md")]
        index = build_page_index(wikilink_fixture_path, content_files)
        resolver = WikilinkResolver(
            index,
            unpublished_refs={"secret"},
            unpublished_policy="warning",
        )
        link = ParsedWikilink(
            raw="[[secret]]",
            page="secret",
            alias=None,
            heading=None,
            block_id=None,
            line_number=9,
        )

        diagnostic = resolver.resolve(link, wikilink_fixture_path / "index.md")

        assert diagnostic is not None
        assert diagnostic.severity == "warning"
        assert "unpublished/excluded" in diagnostic.reason


class TestHeadingNormalization:
    """Tests for heading anchor normalization consistency."""

    def test_heading_normalization_cases(self) -> None:
        extractor = HeadingExtractor()

        # Various heading styles that should normalize to same anchor
        headings = [
            "Installation",
            "installation",
            "INSTALLATION",
            "Installation!",
            "Installation?",
            "Installation (Step 1)",
            "Installation  Step  1",
        ]

        normalized = [extractor.normalize_heading(h) for h in headings]
        # All should normalize to "installation"
        assert all(n == "installation" or n.startswith("installation") for n in normalized)

    def test_special_characters_removed(self) -> None:
        extractor = HeadingExtractor()

        assert extractor.normalize_heading("Hello @#$ World") == "hello-world"
        assert extractor.normalize_heading("100% Complete") == "100-complete"
        assert extractor.normalize_heading("C++ Programming") == "c-programming"


class TestWikilinkDiagnostic:
    """Tests for diagnostic formatting."""

    def test_diagnostic_string_format(self) -> None:
        diagnostic = WikilinkDiagnostic(
            source_file=Path("/vault/about.md"),
            line_number=10,
            raw_link="[[nonexistent]]",
            reason="Page not found: 'nonexistent'",
            severity="error",
        )

        result = str(diagnostic)
        assert "about.md:10:" in result
        assert "[error]" in result
        assert "nonexistent" in result


class TestPageResolutionEdgeCases:
    """Tests for edge cases in page resolution."""

    def test_resolve_with_extension(self, tmp_path: Path) -> None:
        index = PageIndex(tmp_path)
        index.add_page(Path("getting-started.md"), ["getting-started"])

        # Should resolve with or without extension
        assert index.resolve_page("getting-started.md") == Path("getting-started.md")
        assert index.resolve_page("getting-started") == Path("getting-started.md")

    def test_resolve_with_spaces_and_underscores(self, tmp_path: Path) -> None:
        index = PageIndex(tmp_path)
        index.add_page(Path("my-page.md"), ["my-page"])

        # Should resolve various spacing conventions
        assert index.resolve_page("my-page") == Path("my-page.md")
        assert index.resolve_page("my page") == Path("my-page.md")
        assert index.resolve_page("my_page") == Path("my-page.md")
