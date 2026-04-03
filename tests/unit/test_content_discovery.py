"""Tests for content discovery using fixture directories."""

from pathlib import Path

from bullish_ssg.content.discovery import ContentDiscovery, ContentFile


class TestContentDiscovery:
    def test_discovers_markdown_files(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, include_assets=False)

        files = list(discovery.discover())
        paths = {f.relative_path for f in files}

        assert Path("root.md") in paths
        assert Path("file.markdown") in paths
        assert Path("blog/post.md") in paths
        assert Path("docs/guide.md") in paths
        assert Path("docs/reference/api.md") in paths
        assert Path("file.txt") not in paths

    def test_ignores_patterns(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, ignore_patterns=[".obsidian/**", "templates/**"], include_assets=False)

        files = list(discovery.discover())
        paths = {f.relative_path for f in files}

        assert Path(".obsidian/settings.md") not in paths
        assert Path("templates/template.md") not in paths
        assert Path("root.md") in paths

    def test_recursive_discovery(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, include_assets=False)

        files = list(discovery.discover())
        assert len(files) == 7

    def test_discovers_assets(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, include_markdown=False, include_assets=True)

        files = list(discovery.discover())
        paths = {f.relative_path for f in files}

        assert paths == {Path("image.png"), Path("doc.pdf")}

    def test_markdown_only_discovery(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, include_markdown=True, include_assets=False)

        files = list(discovery.discover())
        assert all(f.extension in {".md", ".markdown", ".mdown", ".mkd"} for f in files)

    def test_empty_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "empty"
        vault.mkdir()
        discovery = ContentDiscovery(vault)
        assert list(discovery.discover()) == []

    def test_count(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault, include_assets=False)
        assert discovery.count() == 7

    def test_count_markdown(self, fixture_copy: callable) -> None:
        vault = fixture_copy("content/discovery_tree")
        discovery = ContentDiscovery(vault)
        assert discovery.count_markdown() == 7


class TestContentFile:
    def test_content_file_properties(self, tmp_path: Path) -> None:
        cf = ContentFile(path=tmp_path / "page.md", relative_path=Path("page.md"), extension=".md")
        assert cf.path == tmp_path / "page.md"
        assert cf.relative_path == Path("page.md")
        assert cf.extension == ".md"
