"""Configuration schema for Bullish SSG."""

from enum import Enum
from pathlib import Path
from typing import Optional, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class VaultMode(str, Enum):
    """Vault linking modes."""

    DIRECT = "direct"
    SYMLINK = "symlink"


class SiteConfig(BaseModel):
    """Site configuration section."""

    url: str = Field(..., description="Base URL with trailing slash")
    title: str = Field(..., description="Site title")
    description: Optional[str] = Field(None, description="Site description")
    author: Optional[str] = Field(None, description="Default author")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is absolute and has trailing slash."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Site URL must be absolute (start with http:// or https://)")
        if not v.endswith("/"):
            raise ValueError("Site URL must end with a trailing slash")
        return v


class ContentConfig(BaseModel):
    """Content configuration section."""

    source_dir: Path = Field(Path("docs"), description="Content source directory")
    output_dir: Path = Field(Path("site"), description="Build output directory")
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [".obsidian/**", "templates/**", "_drafts/**"],
        description="Patterns to ignore during discovery",
    )
    blog_dirs: list[str] = Field(
        default_factory=lambda: ["blog", "posts"],
        description="Directories that contain blog posts",
    )
    default_type: str = Field("page", description="Default content type")


class VaultConfig(BaseModel):
    """Vault configuration section."""

    mode: VaultMode = Field(VaultMode.DIRECT, description="Vault linking mode")
    source_path: Optional[Path] = Field(None, description="External vault path (required for symlink mode)")
    link_path: Path = Field(Path("docs"), description="Local path for vault/symlink")

    @model_validator(mode="after")
    def validate_symlink_mode(self) -> Self:
        """Ensure source_path is set when in symlink mode."""
        if self.mode == VaultMode.SYMLINK and self.source_path is None:
            raise ValueError("source_path is required when vault.mode is 'symlink'")
        return self


class ValidationConfig(BaseModel):
    """Validation configuration section."""

    require_date_for_posts: bool = Field(True, description="Require date for posts")
    fail_on_broken_links: bool = Field(True, description="Fail validation on broken links")
    check_heading_anchors: bool = Field(True, description="Validate heading anchors")


class DeployConfig(BaseModel):
    """Deployment configuration section."""

    method: str = Field("gh-pages", description="Deploy method")
    site_dir: Path = Field(Path("site"), description="Site output directory")
    branch: str = Field("gh-pages", description="Target branch for deployment")


class HookConfig(BaseModel):
    """Hook configuration section."""

    pre_build: Optional[str] = Field(None, description="Pre-build hook command")
    post_build: Optional[str] = Field(None, description="Post-build hook command")
    pre_deploy: Optional[str] = Field(None, description="Pre-deploy hook command")
    post_deploy: Optional[str] = Field(None, description="Post-deploy hook command")


class BullishConfig(BaseModel):
    """Complete Bullish SSG configuration."""

    site: SiteConfig
    content: ContentConfig = Field(default_factory=lambda: ContentConfig())
    vault: VaultConfig = Field(default_factory=lambda: VaultConfig())
    validation: ValidationConfig = Field(default_factory=lambda: ValidationConfig())
    deploy: DeployConfig = Field(default_factory=lambda: DeployConfig())
    hooks: HookConfig = Field(default_factory=lambda: HookConfig())
