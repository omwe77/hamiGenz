"""
Configuration loader for hamiGenZ backend.
Provides robust .env loading with precedence preservation.
"""
from pathlib import Path
from typing import Optional, Union


def load_environment(dotenv_path: Optional[Union[str, Path]] = None, override: bool = False) -> bool:
    """
    Load environment variables from .env files.
    By default (override=False), existing environment variables take precedence.

    Args:
        dotenv_path: Optional specific path to a .env file.
        override: Whether .env values should overwrite existing environment variables.

    Returns:
        bool: True if at least one file was successfully loaded, False otherwise.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    if dotenv_path is not None:
        p = Path(dotenv_path)
        if p.is_file():
            return load_dotenv(dotenv_path=p, override=override)
        return False

    backend_dir = Path(__file__).resolve().parent
    loaded = False
    for candidate in [backend_dir / ".env", backend_dir.parent / ".env"]:
        if candidate.is_file():
            if load_dotenv(dotenv_path=candidate, override=override):
                loaded = True
    return loaded
