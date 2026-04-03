"""Configuration loader for Bullish SSG."""

import tomllib
from pathlib import Path

from bullish_ssg.config.schema import BullishConfig

CONFIG_FILENAMES = ["bullish-ssg.toml", "bullish-ssg.config.toml"]


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find config file starting from given path (or cwd) and walking up.

    Args:
        start_path: Path to start search from (defaults to cwd)

    Returns:
        Path to config file if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # First check the start directory
    for filename in CONFIG_FILENAMES:
        config_path = current / filename
        if config_path.exists():
            return config_path

    # Walk up the tree
    while current != current.parent:
        current = current.parent
        for filename in CONFIG_FILENAMES:
            config_path = current / filename
            if config_path.exists():
                return config_path

    return None


def load_config(config_path: Path | None = None) -> BullishConfig:
    """Load configuration from file.

    Args:
        config_path: Explicit config path (optional, will search if not provided)

    Returns:
        Parsed configuration

    Raises:
        FileNotFoundError: If no config file found and none specified
        ValueError: If config is invalid
    """
    if config_path is None:
        config_path = find_config_file()
        if config_path is None:
            raise FileNotFoundError(f"No configuration file found. Searched for: {', '.join(CONFIG_FILENAMES)}")

    config_path = config_path.resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        raw_data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML in config file {config_path}: {e}") from e

    try:
        return BullishConfig.model_validate(raw_data)
    except Exception as e:
        raise ValueError(f"Configuration validation error in {config_path}: {e}") from e


def get_config_path() -> Path | None:
    """Get the path to the config file if one exists.

    Returns:
        Path to config file or None if not found
    """
    return find_config_file()


def has_config() -> bool:
    """Check if a config file exists in the current directory or above.

    Returns:
        True if config exists, False otherwise
    """
    return find_config_file() is not None
