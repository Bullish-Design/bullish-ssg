"""Tests for deployment adapters and preflight."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bullish_ssg.config.schema import (
    BullishConfig,
    ContentConfig,
    DeployConfig,
    HookConfig,
    SiteConfig,
    ValidationConfig,
    VaultConfig,
    VaultMode,
)
from bullish_ssg.deploy.gh_pages import GHPagesDeployer
from bullish_ssg.deploy.branch_pages import BranchPagesDeployer
from bullish_ssg.deploy.preflight import (
    DeployPreflight,
    PreflightResult,
)
from bullish_ssg.render.kiln import CommandResult, KilnAdapter


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_success_result(self) -> None:
        result = PreflightResult(
            passed=True,
            checks=["config", "vault", "build"],
            errors=[],
        )
        assert result.passed is True
        assert len(result.checks) == 3
        assert len(result.errors) == 0

    def test_failure_result(self) -> None:
        result = PreflightResult(
            passed=False,
            checks=["config"],
            errors=["Config file not found"],
        )
        assert result.passed is False
        assert len(result.errors) == 1


class TestDeployPreflight:
    """Tests for DeployPreflight."""

    @pytest.fixture
    def valid_config(self) -> BullishConfig:
        """Create a valid configuration for testing."""
        return BullishConfig(
            site=SiteConfig(
                url="https://example.com/",
                name="Test Site",
            ),
            content=ContentConfig(
                source_dir=Path("docs"),
                output_dir=Path("site"),
            ),
            vault=VaultConfig(
                mode=VaultMode.DIRECT,
                link_path=Path("docs"),
            ),
            validation=ValidationConfig(),
            deploy=DeployConfig(
                method="gh-pages",
                site_dir=Path("site"),
            ),
            hooks=HookConfig(),
        )

    def test_config_validation_success(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that valid config passes."""
        preflight = DeployPreflight(valid_config, cwd=tmp_path)
        result = preflight._validate_config()
        assert result is True

    def test_config_validation_missing_site_name(self, tmp_path: Path) -> None:
        """Test that missing site name fails."""
        config = BullishConfig(
            site=SiteConfig(
                url="https://example.com/",
                name="",
            ),
            content=ContentConfig(),
            vault=VaultConfig(),
            validation=ValidationConfig(),
            deploy=DeployConfig(),
            hooks=HookConfig(),
        )
        preflight = DeployPreflight(config, cwd=tmp_path)
        result = preflight._validate_config()
        assert result is False
        assert any("site name" in e.lower() for e in preflight.errors)

    def test_vault_resolution_success(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that vault path resolves successfully."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        preflight = DeployPreflight(valid_config, cwd=tmp_path)
        result = preflight._validate_vault()

        assert result is True
        assert preflight.vault_path == docs_dir

    def test_vault_resolution_missing_directory(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that missing vault directory fails."""
        preflight = DeployPreflight(valid_config, cwd=tmp_path)
        result = preflight._validate_vault()

        assert result is False
        assert any("docs" in e.lower() for e in preflight.errors)

    def test_build_validation_success(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that successful build passes."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        site_dir = tmp_path / "site"

        # Create mock kiln adapter that returns success
        mock_adapter = MagicMock(spec=KilnAdapter)
        mock_adapter.build.return_value = CommandResult(
            command=["kiln", "generate"],
            returncode=0,
            stdout="Build successful",
            stderr="",
            success=True,
        )

        preflight = DeployPreflight(
            valid_config,
            cwd=tmp_path,
            kiln_adapter=mock_adapter,
        )

        # First validate vault to set vault_path
        preflight._validate_vault()
        result = preflight._validate_build()

        assert result is True
        assert mock_adapter.build.called

    def test_build_validation_failure(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that failed build fails preflight."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create mock kiln adapter that returns failure
        mock_adapter = MagicMock(spec=KilnAdapter)
        mock_adapter.build.return_value = CommandResult(
            command=["kiln", "generate"],
            returncode=1,
            stdout="",
            stderr="Build failed",
            success=False,
        )

        preflight = DeployPreflight(
            valid_config,
            cwd=tmp_path,
            kiln_adapter=mock_adapter,
        )

        # First validate vault to set vault_path
        preflight._validate_vault()
        result = preflight._validate_build()

        assert result is False
        assert any("build failed" in e.lower() for e in preflight.errors)

    def test_full_preflight_success(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that full preflight passes with all checks."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        mock_adapter = MagicMock(spec=KilnAdapter)
        mock_adapter.build.return_value = CommandResult(
            command=["kiln", "generate"],
            returncode=0,
            stdout="Build successful",
            stderr="",
            success=True,
        )

        preflight = DeployPreflight(
            valid_config,
            cwd=tmp_path,
            kiln_adapter=mock_adapter,
        )
        result = preflight.run()

        assert result.passed is True
        assert len(result.checks) == 3
        assert "config" in result.checks
        assert "vault" in result.checks
        assert "build" in result.checks
        mock_adapter.build.assert_called_once_with(
            source_dir=tmp_path / "docs",
            output_dir=tmp_path / "site",
            dry_run=False,
        )

    def test_full_preflight_failure_stops_early(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        """Test that preflight stops on first failure."""
        # Don't create docs directory, so vault validation will fail

        preflight = DeployPreflight(valid_config, cwd=tmp_path)
        result = preflight.run()

        assert result.passed is False
        assert "vault" in result.checks
        # Build should not have been checked since vault failed
        assert not any(c == "build" for c in result.checks)

    def test_preflight_dry_run_uses_dry_build(self, valid_config: BullishConfig, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        mock_adapter = MagicMock(spec=KilnAdapter)
        mock_adapter.build.return_value = CommandResult(
            command=["kiln", "generate", "--source", "docs", "--output", "site"],
            returncode=0,
            stdout="[DRY RUN] kiln generate ...",
            stderr="",
            success=True,
        )

        preflight = DeployPreflight(
            valid_config,
            cwd=tmp_path,
            kiln_adapter=mock_adapter,
        )
        result = preflight.run(dry_run=True)

        assert result.passed is True
        mock_adapter.build.assert_called_once_with(
            source_dir=tmp_path / "docs",
            output_dir=tmp_path / "site",
            dry_run=True,
        )


class TestGHPagesDeployer:
    """Tests for GitHub Pages deployer."""

    @pytest.fixture
    def deploy_config(self) -> DeployConfig:
        return DeployConfig(
            method="gh-pages",
            site_dir=Path("site"),
            branch="main",
        )

    def test_gh_pages_deploy_dry_run(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that dry-run mode constructs correct command."""
        deployer = GHPagesDeployer(deploy_config)
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        result = deployer.deploy(
            site_dir=site_dir,
            dry_run=True,
        )

        assert result.success is True
        assert "[DRY RUN]" in result.stdout
        assert "gh pages deploy" in result.stdout
        assert str(site_dir) in result.stdout

    def test_gh_pages_deploy_command_construction(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that deploy command is constructed correctly."""
        deployer = GHPagesDeployer(deploy_config)
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Mock subprocess runner
        mock_runner = MagicMock()
        mock_runner.run.return_value = CommandResult(
            command=["gh", "pages", "deploy", str(site_dir)],
            returncode=0,
            stdout="Deployed to https://example.github.io/",
            stderr="",
            success=True,
        )
        deployer.runner = mock_runner

        result = deployer.deploy(site_dir=site_dir)

        assert result.success is True
        mock_runner.run.assert_called_once()
        command = mock_runner.run.call_args[0][0]
        assert command[0] == "gh"
        assert command[1] == "pages"
        assert command[2] == "deploy"
        assert str(site_dir) in command

    def test_gh_pages_deploy_missing_site_dir(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that missing site directory fails."""
        deployer = GHPagesDeployer(deploy_config)
        nonexistent_dir = tmp_path / "nonexistent"

        result = deployer.deploy(site_dir=nonexistent_dir)

        assert result.success is False
        assert "does not exist" in result.stderr.lower()

    def test_gh_pages_deploy_failure_propagation(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that gh command failure is propagated."""
        deployer = GHPagesDeployer(deploy_config)
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        mock_runner = MagicMock()
        mock_runner.run.return_value = CommandResult(
            command=["gh", "pages", "deploy", str(site_dir)],
            returncode=1,
            stdout="",
            stderr="gh auth failed",
            success=False,
        )
        deployer.runner = mock_runner

        result = deployer.deploy(site_dir=site_dir)

        assert result.success is False
        assert result.returncode == 1


class TestBranchPagesDeployer:
    """Tests for Branch Pages deployer."""

    @pytest.fixture
    def deploy_config(self) -> DeployConfig:
        return DeployConfig(
            method="branch",
            site_dir=Path("site"),
            branch="main",
            pages_branch="gh-pages",
        )

    def test_branch_deploy_dry_run(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that dry-run mode shows planned actions."""
        deployer = BranchPagesDeployer(deploy_config, cwd=tmp_path)
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        result = deployer.deploy(
            site_dir=site_dir,
            dry_run=True,
        )

        assert result.success is True
        assert "[DRY RUN]" in result.stdout
        assert "gh-pages" in result.stdout

    def test_branch_deploy_command_sequence(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that branch deploy runs git commands."""
        deployer = BranchPagesDeployer(deploy_config, cwd=tmp_path)
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "index.html").write_text("<html></html>")

        # Mock subprocess runner
        mock_runner = MagicMock()
        mock_runner.run.side_effect = [
            # git branch exists check
            CommandResult(
                command=["git", "branch", "--list", "gh-pages"],
                returncode=0,
                stdout="* gh-pages",
                stderr="",
                success=True,
            ),
            # git rev-parse --abbrev-ref HEAD
            CommandResult(
                command=["git", "rev-parse", "--abbrev-ref", "HEAD"],
                returncode=0,
                stdout="main\n",
                stderr="",
                success=True,
            ),
            # git checkout
            CommandResult(
                command=["git", "checkout", "gh-pages"],
                returncode=0,
                stdout="Switched to branch 'gh-pages'",
                stderr="",
                success=True,
            ),
            # git rm -rf .
            CommandResult(
                command=["git", "rm", "-rf", "."],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # git checkout main -- site/
            CommandResult(
                command=["git", "checkout", "main", "--", "site/"],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # mv site/* .
            CommandResult(
                command=["mv", "site/*", "."],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # git add .
            CommandResult(
                command=["git", "add", "."],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # git commit
            CommandResult(
                command=["git", "commit", "-m", "Deploy to gh-pages"],
                returncode=0,
                stdout="[gh-pages abc1234] Deploy to gh-pages",
                stderr="",
                success=True,
            ),
            # git push
            CommandResult(
                command=["git", "push", "origin", "gh-pages"],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # git checkout main
            CommandResult(
                command=["git", "checkout", "main"],
                returncode=0,
                stdout="Switched to branch 'main'",
                stderr="",
                success=True,
            ),
        ]
        deployer.runner = mock_runner

        result = deployer.deploy(site_dir=site_dir)

        assert result.success is True
        # Should have run multiple git commands
        assert mock_runner.run.call_count > 3
        last_cmd = mock_runner.run.call_args_list[-1][0][0]
        assert last_cmd == ["git", "checkout", "main"]

    def test_branch_deploy_creates_pages_branch_if_missing(self, deploy_config: DeployConfig, tmp_path: Path) -> None:
        """Test that deploy creates pages branch if it doesn't exist."""
        deployer = BranchPagesDeployer(deploy_config, cwd=tmp_path)
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "index.html").write_text("<html></html>")

        mock_runner = MagicMock()
        mock_runner.run.side_effect = [
            # git branch exists check - branch not found
            CommandResult(
                command=["git", "branch", "--list", "gh-pages"],
                returncode=0,
                stdout="",
                stderr="",
                success=True,
            ),
            # git rev-parse --abbrev-ref HEAD
            CommandResult(
                command=["git", "rev-parse", "--abbrev-ref", "HEAD"],
                returncode=0,
                stdout="main\n",
                stderr="",
                success=True,
            ),
            # git checkout --orphan
            CommandResult(
                command=["git", "checkout", "--orphan", "gh-pages"],
                returncode=0,
                stdout="Switched to a new branch 'gh-pages'",
                stderr="",
                success=True,
            ),
            # ... more commands
            CommandResult(command=["git", "rm", "-rf", "."], returncode=0, stdout="", stderr="", success=True),
            CommandResult(
                command=["git", "checkout", "main", "--", "site/"], returncode=0, stdout="", stderr="", success=True
            ),
            CommandResult(command=["mv", "site/*", "."], returncode=0, stdout="", stderr="", success=True),
            CommandResult(command=["git", "add", "."], returncode=0, stdout="", stderr="", success=True),
            CommandResult(
                command=["git", "commit", "-m", "Deploy to gh-pages"], returncode=0, stdout="", stderr="", success=True
            ),
            CommandResult(
                command=["git", "push", "origin", "gh-pages"], returncode=0, stdout="", stderr="", success=True
            ),
            CommandResult(command=["git", "checkout", "main"], returncode=0, stdout="", stderr="", success=True),
        ]
        deployer.runner = mock_runner

        result = deployer.deploy(site_dir=site_dir)

        assert result.success is True
        # Should have created orphan branch
        calls = [call[0][0] for call in mock_runner.run.call_args_list]
        assert any("--orphan" in str(cmd) for cmd in calls)

    def test_branch_deploy_fails_when_current_branch_unknown(
        self,
        deploy_config: DeployConfig,
        tmp_path: Path,
    ) -> None:
        deployer = BranchPagesDeployer(deploy_config, cwd=tmp_path)
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        mock_runner = MagicMock()
        mock_runner.run.side_effect = [
            CommandResult(
                command=["git", "branch", "--list", "gh-pages"],
                returncode=0,
                stdout="* gh-pages",
                stderr="",
                success=True,
            ),
            CommandResult(
                command=["git", "rev-parse", "--abbrev-ref", "HEAD"],
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository",
                success=False,
            ),
        ]
        deployer.runner = mock_runner

        result = deployer.deploy(site_dir=site_dir)

        assert result.success is False
        assert result.command == ["git", "rev-parse", "--abbrev-ref", "HEAD"]

