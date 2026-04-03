"""GitHub Pages deployment adapter."""

from pathlib import Path
from typing import Optional

from bullish_ssg.config.schema import DeployConfig
from bullish_ssg.render.kiln import CommandResult, SubprocessRunner


class GHPagesDeployer:
    """Deployer using 'gh pages deploy' command."""

    def __init__(
        self,
        config: DeployConfig,
        runner: Optional[SubprocessRunner] = None,
    ) -> None:
        """Initialize GitHub Pages deployer.

        Args:
            config: Deploy configuration
            runner: Optional subprocess runner for testing
        """
        self.config = config
        self.runner = runner or SubprocessRunner()

    def deploy(
        self,
        site_dir: Path,
        dry_run: bool = False,
    ) -> CommandResult:
        """Deploy site using gh pages deploy.

        Args:
            site_dir: Directory containing built site
            dry_run: If True, construct command without executing

        Returns:
            CommandResult from deploy execution
        """
        # Validate site directory exists
        if not site_dir.exists():
            return CommandResult(
                command=["gh", "pages", "deploy", str(site_dir)],
                returncode=1,
                stdout="",
                stderr=f"Site directory does not exist: {site_dir}",
                success=False,
            )

        command = ["gh", "pages", "deploy", str(site_dir)]

        if dry_run:
            return CommandResult(
                command=command,
                returncode=0,
                stdout=f"[DRY RUN] Would execute: {' '.join(command)}",
                stderr="",
                success=True,
            )

        return self.runner.run(command)

    def get_deploy_url(self) -> str:
        """Get the expected deploy URL.

        Returns:
            URL where site will be deployed
        """
        # gh pages deploy typically uses the repo's GitHub Pages URL
        return "https://<owner>.github.io/<repo>/"
