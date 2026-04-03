"""Deploy preflight checks."""

from dataclasses import dataclass, field
from pathlib import Path

from bullish_ssg.config.schema import BullishConfig
from bullish_ssg.render.kiln import KilnAdapter
from bullish_ssg.vault_link.resolver import VaultResolver


@dataclass
class PreflightResult:
    """Result of preflight validation."""

    passed: bool
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Return True if preflight passed."""
        return self.passed


class DeployPreflight:
    """Pre-flight checks before deployment."""

    def __init__(
        self,
        config: BullishConfig,
        cwd: Path | None = None,
        kiln_adapter: KilnAdapter | None = None,
    ) -> None:
        """Initialize preflight checker.

        Args:
            config: Bullish configuration
            cwd: Working directory (defaults to current directory)
            kiln_adapter: Optional Kiln adapter for build testing
        """
        self.config = config
        self.cwd = cwd or Path.cwd()
        self.kiln = kiln_adapter or KilnAdapter()
        self.errors: list[str] = []
        self.vault_path: Path | None = None

    def run(self, dry_run: bool = False) -> PreflightResult:
        """Run all preflight checks.

        Args:
            dry_run: When True, run build validation in dry-run mode.

        Returns:
            PreflightResult with pass/fail status and any errors
        """
        self.errors = []
        checks: list[str] = []

        # Check 1: Config validation
        if not self._validate_config():
            checks.append("config")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=self.errors,
            )
        checks.append("config")

        # Check 2: Vault resolution
        if not self._validate_vault():
            checks.append("vault")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=self.errors,
            )
        checks.append("vault")

        # Check 3: Build validation
        if not self._validate_build(dry_run=dry_run):
            checks.append("build")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=self.errors,
            )
        checks.append("build")

        return PreflightResult(
            passed=True,
            checks=checks,
            errors=[],
        )

    def _validate_config(self) -> bool:
        """Validate configuration is complete.

        Returns:
            True if config is valid
        """
        # Check site config
        if not self.config.site.url:
            self.errors.append("Site URL is not configured")
            return False

        if not self.config.site.name:
            self.errors.append("Site name is not configured")
            return False

        # Check deploy config
        if not self.config.deploy.method:
            self.errors.append("Deploy method is not configured")
            return False

        valid_methods = ["gh-pages", "branch"]
        if self.config.deploy.method not in valid_methods:
            self.errors.append(
                f"Invalid deploy method: {self.config.deploy.method}. Must be one of: {', '.join(valid_methods)}"
            )
            return False

        return True

    def _validate_vault(self) -> bool:
        """Validate vault path is resolvable.

        Returns:
            True if vault is accessible
        """
        try:
            resolver = VaultResolver(self.config.vault, self.cwd)
            self.vault_path = resolver.resolve()
            return True
        except Exception as e:
            self.errors.append(f"Vault resolution failed: {e}")
            return False

    def _validate_build(self, dry_run: bool = False) -> bool:
        """Validate that build succeeds.

        Args:
            dry_run: When True, verify build command path without executing kiln.

        Returns:
            True if build succeeds
        """
        if self.vault_path is None:
            self.errors.append("Cannot validate build without vault path")
            return False

        output_dir = self.cwd / self.config.deploy.site_dir

        try:
            result = self.kiln.build(
                source_dir=self.vault_path,
                output_dir=output_dir,
                dry_run=dry_run,
            )

            if not result.success:
                self.errors.append(f"Build failed with exit code {result.returncode}")
                if result.stderr:
                    self.errors.append(f"Build error: {result.stderr}")
                return False

            return True
        except Exception as e:
            self.errors.append(f"Build validation failed: {e}")
            return False
