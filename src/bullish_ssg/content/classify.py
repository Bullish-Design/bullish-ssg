"""Content classification and routing for vault files."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class ContentType(StrEnum):
    """Content type constants."""

    PAGE = "page"
    POST = "post"
    DOC = "doc"


class ClassificationError(Exception):
    """Raised when content cannot be classified safely."""


class SlugCollisionError(Exception):
    """Raised when slug collisions are detected."""


@dataclass
class ContentRoute:
    """Represents the computed route for a content file."""

    source_path: Path
    relative_path: Path
    content_type: str
    slug: str
    date: datetime | None
    permalink: str
    draft: bool


class ContentClassifier:
    """Classifies content and generates routing metadata."""

    def __init__(
        self,
        vault_path: Path,
        blog_dirs: list[str] | None = None,
        default_type: str = ContentType.DOC,
        require_date_for_posts: bool = True,
        posts_url_style: str = "date-slug",
    ) -> None:
        """Initialize classifier with configuration."""
        self.vault_path = vault_path.resolve()
        self.blog_dirs = set(blog_dirs or ["blog", "posts"])
        self.default_type = default_type
        self.require_date_for_posts = require_date_for_posts
        self.posts_url_style = posts_url_style

    def classify(self, relative_path: Path, metadata: dict[str, Any]) -> ContentRoute:
        """Classify a content file and generate routing metadata."""
        content_type = self._infer_type(relative_path, metadata)
        slug = self._generate_slug(relative_path, metadata)
        date = self._parse_date(metadata.get("date"), content_type)
        draft = bool(metadata.get("draft", False))
        permalink = self._build_permalink(content_type, slug, date, relative_path)

        return ContentRoute(
            source_path=self.vault_path / relative_path,
            relative_path=relative_path,
            content_type=content_type,
            slug=slug,
            date=date,
            permalink=permalink,
            draft=draft,
        )

    def _infer_type(self, relative_path: Path, metadata: dict[str, Any]) -> str:
        """Infer content type from metadata and path."""
        if "type" in metadata:
            explicit_type = str(metadata["type"]).lower()
            if explicit_type not in {ContentType.PAGE, ContentType.POST, ContentType.DOC}:
                raise ClassificationError(
                    f"Unsupported content type '{metadata['type']}' for {relative_path}. "
                    f"Expected one of: {ContentType.PAGE}, {ContentType.POST}, {ContentType.DOC}"
                )
            return explicit_type

        first_part = relative_path.parts[0] if relative_path.parts else ""
        if first_part in self.blog_dirs:
            return ContentType.POST

        return self.default_type

    def _generate_slug(self, relative_path: Path, metadata: dict[str, Any]) -> str:
        """Generate URL slug from metadata or filename."""
        if "slug" in metadata:
            slug = self._normalize_slug(str(metadata["slug"]))
            if slug:
                return slug
            raise ClassificationError(f"Slug cannot be empty after normalization for {relative_path}")

        slug = self._normalize_slug(relative_path.stem)
        if slug:
            return slug
        raise ClassificationError(f"Could not derive non-empty slug from filename: {relative_path}")

    def _normalize_slug(self, slug: str) -> str:
        """Normalize a slug for URL use."""
        slug = slug.lower()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")

    def _parse_date(self, date_value: Any, content_type: str) -> datetime | None:
        """Parse date from various formats."""
        if date_value is None:
            if content_type == ContentType.POST and self.require_date_for_posts:
                raise ClassificationError("Post content requires a valid 'date' field")
            return None

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())

        if isinstance(date_value, str):
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%d/%m/%Y",
                "%m/%d/%Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue

        if content_type == ContentType.POST and self.require_date_for_posts:
            raise ClassificationError(f"Invalid post date value: {date_value!r}")
        return None

    def _build_permalink(
        self,
        content_type: str,
        slug: str,
        date: datetime | None,
        relative_path: Path,
    ) -> str:
        """Build permalink from content info."""
        if content_type == ContentType.POST and date:
            if self.posts_url_style == "date-slug":
                return f"/blog/{date.year:04d}/{date.month:02d}/{date.day:02d}/{slug}/"
            if self.posts_url_style == "slug":
                return f"/blog/{slug}/"
            raise ClassificationError(
                f"Unsupported posts_url_style '{self.posts_url_style}'. Expected 'date-slug' or 'slug'."
            )

        if content_type == ContentType.POST:
            return f"/blog/{slug}/"

        parent = relative_path.parent
        if parent == Path("."):
            return f"/{slug}/"
        return f"/{parent}/{slug}/"


def check_slug_collisions(routes: list[ContentRoute]) -> list[tuple[ContentRoute, ContentRoute]]:
    """Check for duplicate permalinks in routes."""
    by_permalink: dict[str, list[ContentRoute]] = {}

    for route in routes:
        by_permalink.setdefault(route.permalink, []).append(route)

    collisions: list[tuple[ContentRoute, ContentRoute]] = []
    for routes_with_permalink in by_permalink.values():
        if len(routes_with_permalink) > 1:
            for i in range(len(routes_with_permalink)):
                for j in range(i + 1, len(routes_with_permalink)):
                    collisions.append((routes_with_permalink[i], routes_with_permalink[j]))

    return collisions


def enforce_no_slug_collisions(routes: list[ContentRoute]) -> None:
    """Raise SlugCollisionError if duplicate permalinks exist."""
    collisions = check_slug_collisions(routes)
    if not collisions:
        return

    first, second = collisions[0]
    raise SlugCollisionError(
        "Detected permalink collision:\n"
        f"  {first.permalink} -> {first.relative_path}\n"
        f"  {second.permalink} -> {second.relative_path}\n"
        "Adjust slugs or content paths to make permalinks unique."
    )
