"""Kiln renderer adapter for Bullish SSG."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class KilnError(Exception):
    """Raised when Kiln command fails."""

    pass


@dataclass
class CommandResult:
    """Result of a command execution."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    success: bool

    def __str__(self) -> str:
        cmd_str = " ".join(self.command)
        status = "succeeded" if self.success else "failed"
        return f"Command '{cmd_str}' {status} with code {self.returncode}"


class SubprocessRunner:
    """Wrapper for subprocess execution with result capture."""

    def run(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        capture_output: bool = True,
    ) -> CommandResult:
        """Run a command and capture result.

        Args:
            command: Command and arguments as list
            cwd: Working directory for command
            capture_output: Whether to capture stdout/stderr

        Returns:
            CommandResult with execution details

        Raises:
            KilnError: If command execution fails catastrophically
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=False,
            )

            return CommandResult(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                success=result.returncode == 0,
            )
        except FileNotFoundError as e:
            raise KilnError(f"Command not found: {command[0]}. Ensure Kiln is installed and in PATH.") from e
        except subprocess.SubprocessError as e:
            raise KilnError(f"Failed to execute command: {e}") from e


class KilnAdapter:
    """Adapter for Kiln static site generator commands."""

    def __init__(
        self,
        runner: Optional[SubprocessRunner] = None,
    ) -> None:
        """Initialize adapter.

        Args:
            runner: Subprocess runner for command execution (mockable for tests)
        """
        self.runner = runner or SubprocessRunner()

    def build(
        self,
        source_dir: Path,
        output_dir: Path,
        config_file: Optional[Path] = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build the static site using kiln generate.

        Args:
            source_dir: Source directory for content
            output_dir: Output directory for generated site
            config_file: Optional Kiln config file
            dry_run: If True, only construct and return command without execution

        Returns:
            CommandResult from execution or dry-run
        """
        command = ["kiln", "generate"]

        # Add source directory
        command.extend(["--source", str(source_dir)])

        # Add output directory
        command.extend(["--output", str(output_dir)])

        # Add config file if specified
        if config_file:
            command.extend(["--config", str(config_file)])

        if dry_run:
            return CommandResult(
                command=command,
                returncode=0,
                stdout=f"[DRY RUN] Would execute: {' '.join(command)}",
                stderr="",
                success=True,
            )

        return self.runner.run(command)

    def serve(
        self,
        source_dir: Path,
        port: int = 8000,
        config_file: Optional[Path] = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Serve the site locally using kiln serve.

        Args:
            source_dir: Source directory for content
            port: Port to serve on
            config_file: Optional Kiln config file
            dry_run: If True, only construct and return command without execution

        Returns:
            CommandResult from execution or dry-run
        """
        command = ["kiln", "serve"]

        # Add source directory
        command.extend(["--source", str(source_dir)])

        # Add port
        command.extend(["--port", str(port)])

        # Add config file if specified
        if config_file:
            command.extend(["--config", str(config_file)])

        if dry_run:
            return CommandResult(
                command=command,
                returncode=0,
                stdout=f"[DRY RUN] Would execute: {' '.join(command)}",
                stderr="",
                success=True,
            )

        return self.runner.run(command)


class BuildManager:
    """High-level build management with config integration."""

    def __init__(
        self,
        kiln_adapter: Optional[KilnAdapter] = None,
    ) -> None:
        """Initialize build manager.

        Args:
            kiln_adapter: Kiln adapter for command execution
        """
        self.kiln = kiln_adapter or KilnAdapter()

    def build_from_config(
        self,
        vault_path: Path,
        output_dir: Path,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build site from configuration.

        Args:
            vault_path: Resolved vault path with content
            output_dir: Output directory for site
            dry_run: If True, only show what would be done

        Returns:
            CommandResult from build execution
        """
        return self.kiln.build(
            source_dir=vault_path,
            output_dir=output_dir,
            dry_run=dry_run,
        )

    def serve_from_config(
        self,
        vault_path: Path,
        port: int = 8000,
        dry_run: bool = False,
    ) -> CommandResult:
        """Serve site from configuration.

        Args:
            vault_path: Resolved vault path with content
            port: Port to serve on
            dry_run: If True, only show what would be done

        Returns:
            CommandResult from serve execution
        """
        return self.kiln.serve(
            source_dir=vault_path,
            port=port,
            dry_run=dry_run,
        )
