"""Tests for Kiln render adapter."""

from pathlib import Path

import pytest

from bullish_ssg.render.kiln import (
    BuildManager,
    CommandResult,
    KilnAdapter,
    KilnError,
    SubprocessRunner,
)


class MockSubprocessRunner:
    """Mock runner for testing."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.commands: list[list[str]] = []

    def run(
        self,
        command: list[str],
        cwd: Path | None = None,
        capture_output: bool = True,
    ) -> CommandResult:
        self.commands.append(command)
        return CommandResult(
            command=command,
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            success=self.returncode == 0,
        )


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_result(self) -> None:
        result = CommandResult(
            command=["kiln", "generate"],
            returncode=0,
            stdout="Build complete",
            stderr="",
            success=True,
        )
        assert result.success is True
        assert "succeeded" in str(result).lower()

    def test_failure_result(self) -> None:
        result = CommandResult(
            command=["kiln", "generate"],
            returncode=1,
            stdout="",
            stderr="Error occurred",
            success=False,
        )
        assert result.success is False
        assert "failed" in str(result).lower()


class TestKilnAdapter:
    """Tests for KilnAdapter."""

    def test_build_command_construction(self) -> None:
        mock_runner = MockSubprocessRunner()
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")
        output_dir = Path("/output")

        result = adapter.build(source_dir, output_dir)

        assert result.success is True
        assert len(mock_runner.commands) == 1
        command = mock_runner.commands[0]
        assert command[0] == "kiln"
        assert command[1] == "generate"
        assert "--source" in command
        assert str(source_dir) in command
        assert "--output" in command
        assert str(output_dir) in command

    def test_build_with_config_file(self) -> None:
        mock_runner = MockSubprocessRunner()
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")
        output_dir = Path("/output")
        config_file = Path("/config.toml")

        result = adapter.build(source_dir, output_dir, config_file=config_file)

        assert "--config" in mock_runner.commands[0]
        assert str(config_file) in mock_runner.commands[0]

    def test_build_dry_run(self) -> None:
        mock_runner = MockSubprocessRunner()
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")
        output_dir = Path("/output")

        result = adapter.build(source_dir, output_dir, dry_run=True)

        # Dry run should not execute
        assert len(mock_runner.commands) == 0
        assert result.success is True
        assert "[DRY RUN]" in result.stdout
        assert "kiln generate" in result.stdout

    def test_serve_command_construction(self) -> None:
        mock_runner = MockSubprocessRunner()
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")

        result = adapter.serve(source_dir, port=3000)

        assert result.success is True
        command = mock_runner.commands[0]
        assert command[0] == "kiln"
        assert command[1] == "serve"
        assert "--source" in command
        assert "--port" in command
        assert "3000" in command

    def test_serve_dry_run(self) -> None:
        mock_runner = MockSubprocessRunner()
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")

        result = adapter.serve(source_dir, port=8000, dry_run=True)

        assert len(mock_runner.commands) == 0
        assert "[DRY RUN]" in result.stdout
        assert "kiln serve" in result.stdout

    def test_subprocess_failure_propagation(self) -> None:
        mock_runner = MockSubprocessRunner(returncode=1, stderr="Build failed")
        adapter = KilnAdapter(runner=mock_runner)
        source_dir = Path("/content")
        output_dir = Path("/output")

        result = adapter.build(source_dir, output_dir)

        assert result.success is False
        assert result.returncode == 1
        assert result.stderr == "Build failed"


class TestBuildManager:
    """Tests for BuildManager."""

    def test_build_from_config(self) -> None:
        mock_runner = MockSubprocessRunner()
        kiln = KilnAdapter(runner=mock_runner)
        manager = BuildManager(kiln_adapter=kiln)
        vault_path = Path("/vault")
        output_dir = Path("/site")

        result = manager.build_from_config(
            vault_path=vault_path,
            output_dir=output_dir,
        )

        assert result.success is True
        command = mock_runner.commands[0]
        assert str(vault_path) in command
        assert str(output_dir) in command

    def test_serve_from_config(self) -> None:
        mock_runner = MockSubprocessRunner()
        kiln = KilnAdapter(runner=mock_runner)
        manager = BuildManager(kiln_adapter=kiln)
        vault_path = Path("/vault")

        result = manager.serve_from_config(
            vault_path=vault_path,
            port=8000,
        )

        assert result.success is True
        command = mock_runner.commands[0]
        assert str(vault_path) in command
        assert "8000" in command


class TestSubprocessRunner:
    """Tests for SubprocessRunner with real subprocess."""

    def test_run_successful_command(self) -> None:
        runner = SubprocessRunner()
        result = runner.run(["echo", "hello"])

        assert result.success is True
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_with_cwd(self, tmp_path: Path) -> None:
        runner = SubprocessRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = runner.run(["pwd"], cwd=tmp_path)

        assert result.success is True
        assert str(tmp_path) in result.stdout or tmp_path.name in result.stdout

    def test_run_failure_command(self) -> None:
        runner = SubprocessRunner()
        result = runner.run(["false"])

        assert result.success is False
        assert result.returncode == 1

    def test_command_not_found_raises_kiln_error(self) -> None:
        runner = SubprocessRunner()
        with pytest.raises(KilnError) as exc_info:
            runner.run(["nonexistent_command_xyz"])

        assert "not found" in str(exc_info.value).lower()


class TestKilnError:
    """Tests for KilnError exception."""

    def test_error_message(self) -> None:
        error = KilnError("Test error")
        assert str(error) == "Test error"

    def test_error_from_exception(self) -> None:
        original = ValueError("Original error")
        try:
            raise KilnError("Wrapped error") from original
        except KilnError as e:
            assert "Wrapped error" in str(e)
            assert e.__cause__ is original
