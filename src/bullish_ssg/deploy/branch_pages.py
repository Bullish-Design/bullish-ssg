"""Branch-based deployment adapter for GitHub Pages."""

from pathlib import Path

from bullish_ssg.config.schema import DeployConfig
from bullish_ssg.deploy.url import infer_pages_url
from bullish_ssg.render.kiln import CommandResult, SubprocessRunner


class BranchPagesDeployer:
    """Deployer using git branch workflow for GitHub Pages."""

    def __init__(
        self,
        config: DeployConfig,
        cwd: Path | None = None,
        runner: SubprocessRunner | None = None,
    ) -> None:
        """Initialize branch-based deployer.

        Args:
            config: Deploy configuration
            cwd: Working directory for git commands
            runner: Optional subprocess runner for testing
        """
        self.config = config
        self.cwd = cwd or Path.cwd()
        self.runner = runner or SubprocessRunner()

    def deploy(
        self,
        site_dir: Path,
        dry_run: bool = False,
    ) -> CommandResult:
        """Deploy site by pushing to pages branch.

        This workflow:
        1. Check if pages branch exists
        2. Create or checkout pages branch
        3. Clear branch contents
        4. Copy site files
        5. Commit and push
        6. Return to original branch

        Args:
            site_dir: Directory containing built site
            dry_run: If True, show what would be done

        Returns:
            CommandResult from deploy execution
        """
        if not site_dir.exists():
            return CommandResult(
                command=[],
                returncode=1,
                stdout="",
                stderr=f"Site directory does not exist: {site_dir}",
                success=False,
            )

        pages_branch = self.config.pages_branch
        source_branch = self.config.branch

        if dry_run:
            commands = [
                f"git branch --list {pages_branch}",
                f"git checkout {pages_branch} (or create --orphan)",
                "git rm -rf .",
                f"git checkout {source_branch} -- {self.config.site_dir}/",
                "mv site/* .",
                f'git commit -m "Deploy to {pages_branch}"',
                f"git push origin {pages_branch}",
                f"git checkout {source_branch}",
            ]
            return CommandResult(
                command=[],
                returncode=0,
                stdout="[DRY RUN] Would execute:\n" + "\n".join(commands),
                stderr="",
                success=True,
            )

        # Require clean working tree for safer branch switching.
        dirty_check = self.runner.run(["git", "status", "--porcelain"], cwd=self.cwd)
        if not dirty_check.success:
            return dirty_check
        if dirty_check.stdout.strip():
            return CommandResult(
                command=["git", "status", "--porcelain"],
                returncode=1,
                stdout=dirty_check.stdout,
                stderr="Refusing deploy: working tree has uncommitted changes",
                success=False,
            )

        # Check if pages branch exists
        branch_check = self.runner.run(
            ["git", "branch", "--list", pages_branch],
            cwd=self.cwd,
        )

        if not branch_check.success:
            return branch_check

        branch_exists = pages_branch in branch_check.stdout

        # Get current branch to return to later
        current_branch_result = self.runner.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.cwd,
        )
        if not current_branch_result.success:
            return current_branch_result

        original_branch = current_branch_result.stdout.strip()
        if not original_branch:
            return CommandResult(
                command=["git", "rev-parse", "--abbrev-ref", "HEAD"],
                returncode=1,
                stdout="",
                stderr="Unable to determine current branch for deploy rollback",
                success=False,
            )

        try:
            # Checkout or create pages branch
            if branch_exists:
                result = self.runner.run(
                    ["git", "checkout", pages_branch],
                    cwd=self.cwd,
                )
            else:
                result = self.runner.run(
                    ["git", "checkout", "--orphan", pages_branch],
                    cwd=self.cwd,
                )

            if not result.success:
                return result

            # Clear branch (keep .git)
            result = self.runner.run(
                ["git", "rm", "-rf", "."],
                cwd=self.cwd,
            )
            # Ignore error if nothing to remove

            # Copy site content from source branch
            result = self.runner.run(
                ["git", "checkout", source_branch, "--", str(self.config.site_dir)],
                cwd=self.cwd,
            )
            if not result.success:
                return result

            # Move site content to root
            site_path = self.cwd / self.config.site_dir
            if site_path.exists():
                # Move all contents from site_dir to cwd
                for item in site_path.iterdir():
                    target = self.cwd / item.name
                    # Use mv command for simplicity
                    result = self.runner.run(
                        ["mv", str(item), str(target)],
                        cwd=self.cwd,
                    )
                    if not result.success:
                        return result

            # Commit
            result = self.runner.run(
                ["git", "add", "."],
                cwd=self.cwd,
            )
            if not result.success:
                return result

            result = self.runner.run(
                ["git", "commit", "-m", f"Deploy to {pages_branch}"],
                cwd=self.cwd,
            )
            # Ignore "nothing to commit" errors

            # Push
            result = self.runner.run(
                ["git", "push", "origin", pages_branch],
                cwd=self.cwd,
            )
            if not result.success:
                return result

            return CommandResult(
                command=["git", "push", "origin", pages_branch],
                returncode=0,
                stdout=f"Deployed to {pages_branch} branch",
                stderr="",
                success=True,
            )

        finally:
            # Always return to original branch
            self.runner.run(
                ["git", "checkout", original_branch],
                cwd=self.cwd,
            )

    def get_deploy_url(self) -> str:
        """Get the expected deploy URL.

        Returns:
            URL where site will be deployed
        """
        remote_result = self.runner.run(["git", "remote", "get-url", "origin"], cwd=self.cwd)
        if remote_result.success:
            inferred = infer_pages_url(remote_result.stdout)
            if inferred is not None:
                return f"{inferred} (from {self.config.pages_branch} branch)"
        return f"GitHub Pages URL (from {self.config.pages_branch} branch)"
