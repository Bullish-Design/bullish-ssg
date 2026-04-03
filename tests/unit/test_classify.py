"""Tests for content classification and routing using fixture data."""

from datetime import date
from pathlib import Path

import pytest

from bullish_ssg.content.classify import (
    ClassificationError,
    ContentClassifier,
    ContentType,
    SlugCollisionError,
    enforce_no_slug_collisions,
)
from bullish_ssg.content.frontmatter import FrontmatterParser


@pytest.fixture
def classifier(fixture_file: callable) -> ContentClassifier:
    return ContentClassifier(vault_path=fixture_file("classification"), require_date_for_posts=True)


def test_frontmatter_type_overrides_path_inference(classifier: ContentClassifier) -> None:
    route = classifier.classify(Path("guides/getting-started.md"), {"type": "page"})
    assert route.content_type == ContentType.PAGE


def test_blog_path_infers_post_type(classifier: ContentClassifier) -> None:
    route = classifier.classify(Path("blog/post-with-date.md"), {"date": "2026-04-03"})
    assert route.content_type == ContentType.POST


def test_slug_generation_and_normalization(classifier: ContentClassifier) -> None:
    route = classifier.classify(Path("guides/getting-started.md"), {"slug": "My Slug_Value"})
    assert route.slug == "my-slug-value"


def test_post_requires_date_when_configured(classifier: ContentClassifier) -> None:
    with pytest.raises(ClassificationError):
        classifier.classify(Path("blog/post-no-date.md"), {"type": "post"})


def test_route_generation_date_slug_style(classifier: ContentClassifier) -> None:
    route = classifier.classify(
        Path("blog/post-with-date.md"),
        {"type": "post", "date": "2026-04-03", "slug": "post-with-date"},
    )
    assert route.permalink == "/blog/2026/04/03/post-with-date/"


def test_collision_detection_raises(fixture_file: callable) -> None:
    parser = FrontmatterParser(fixture_file("classification/duplicate"))
    classifier = ContentClassifier(vault_path=fixture_file("classification/duplicate"))

    a = parser.parse(fixture_file("classification/duplicate/a.md"))
    b = parser.parse(fixture_file("classification/duplicate/b.md"))

    routes = [
        classifier.classify(Path("a.md"), a.metadata),
        classifier.classify(Path("b.md"), b.metadata),
    ]

    with pytest.raises(SlugCollisionError):
        enforce_no_slug_collisions(routes)


def test_post_date_accepts_python_date_object(classifier: ContentClassifier) -> None:
    route = classifier.classify(
        Path("blog/post-with-date.md"),
        {"type": "post", "date": date(2026, 4, 3), "slug": "post-with-date"},
    )
    assert route.date is not None
    assert route.date.year == 2026
    assert route.date.month == 4
    assert route.date.day == 3
