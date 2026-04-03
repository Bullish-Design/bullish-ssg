"""Tests for content discovery."""

from pathlib import Path

import pytest

from bullish_ssg.content.discovery import ContentDiscovery, ContentFile


class TestContentDiscovery:
    """Tests for ContentDiscovery class."""

    def test_discovers_markdown_files(self, tmp_path: Path) -> None:
        """Test that markdown files are discovered."""
        (tmp_path / "page.md").write_text("# Page")
        (tmp_path / "post.md").write_text("# Post")

        discovery = ContentDiscovery(tmp_path)
        files = list(discovery.discover())

        assert len(files) == 2
        paths = {f.relative_path for f in files}
        assert paths == {Path("page.md"), Path("post.md")}

    def test_discovers_with_extensions(self, tmp_path: Path) -> None:
        """Test discovery of various markdown extensions."""
        (tmp_path / "file.md").write_text("# MD")
        (tmp_path / "file.markdown").write_text("# Markdown")
        (tmp_path / "file.txt").write_text("Not markdown")

        discovery = ContentDiscovery(tmp_path)
        files = list(discovery.discover())

        paths = {f.relative_path for f in files}
        assert Path("file.md") in paths
        assert Path("file.markdown") in paths
        assert Path("file.txt") not in paths

    def test_ignores_patterns(self, tmp_path: Path) -> None:
        """Test that ignore patterns are respected."""
        (tmp_path / "page.md").write_text("# Page")
        (tmp_path / ".obsidian").mkdir()
        (tmp_path / ".obsidian" / "settings.md").write_text("settings")
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "template.md").write_text("template")

        discovery = ContentDiscovery(tmp_path, ignore_patterns=[".obsidian/**", "templates/**"])
        files = list(discovery.discover())

        assert len(files) == 1
        assert files[0].relative_path == Path("page.md")

    def test_recursive_discovery(self, tmp_path: Path) -> None:
        """Test recursive directory traversal."""
        (tmp_path / "root.md").write_text("# Root")
        (tmp_path / "blog").mkdir()
        (tmp_path / "blog" / "post.md").write_text("# Post")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide")
        (tmp_path / "docs" / "reference").mkdir()
        (tmp_path / "docs" / "reference" / "api.md").write_text("# API")

        discovery = ContentDiscovery(tmp_path)
        files = list(discovery.discover())

        assert len(files) == 4
        paths = {f.relative_path for f in files}
        assert Path("root.md") in paths
        assert Path("blog/post.md") in paths
        assert Path("docs/guide.md") in paths
        assert Path("docs/reference/api.md") in paths

    def test_discovers_assets(self, tmp_path: Path) -> None:
        """Test that asset files are discovered when enabled."""
        (tmp_path / "image.png").write_text("png data")
        (tmp_path / "doc.pdf").write_text("pdf data")

        discovery = ContentDiscovery(tmp_path, include_markdown=False, include_assets=True)
        files = list(discovery.discover())

        assert len(files) == 2
        paths = {f.relative_path for f in files}
        assert Path("image.png") in paths
        assert Path("doc.pdf") in paths

    def test_markdown_only_discovery(self, tmp_path: Path) -> None:
        """Test discovering only markdown files."""
        (tmp_path / "page.md").write_text("# Page")
        (tmp_path / "image.png").write_text("png")
        (tmp_path / "doc.pdf").write_text("pdf")

        discovery = ContentDiscovery(tmp_path, include_markdown=True, include_assets=False)
        files = list(discovery.discover())

        assert len(files) == 1
        assert files[0].relative_path == Path("page.md")

    def test_empty_vault(self, tmp_path: Path) -> None:
        """Test discovery in empty vault."""
        discovery = ContentDiscovery(tmp_path)
        files = list(discovery.discover())
        assert len(files) == 0

    def test_count(self, tmp_path: Path) -> None:
        """Test count method."""
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")
        (tmp_path / "c.md").write_text("# C")

        discovery = ContentDiscovery(tmp_path)
        assert discovery.count() == 3

    def test_count_markdown(self, tmp_path: Path) -> None:
        """Test count_markdown method."""
        (tmp_path / "page.md").write_text("# Page")
        (tmp_path / "image.png").write_text("png")

        discovery = ContentDiscovery(tmp_path)
        assert discovery.count_markdown() == 1


class TestContentFile:
    """Tests for ContentFile dataclass."""

    def test_content_file_properties(self, tmp_path: Path) -> None:
        """Test ContentFile properties."""
        cf = ContentFile(path=tmp_path / "page.md", relative_path=Path("page.md"), extension=".md")
        assert cf.path == tmp_path / "page.md"
        assert cf.relative_path == Path("page.md")
        assert cf.extension == ".md"

    def test_content_file_extensions_normalized(self, tmp_path: Path) -> None:
        """Test that extensions are normalized."""
        cf = ContentFile(path=tmp_path / "file.MD", relative_path=Path("file.MD"), extension=".md")
        assert cf.extension == ".md"
