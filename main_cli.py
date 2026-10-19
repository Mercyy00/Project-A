"""Central CLI Terminal Runner for Project Jarvis.

Allows Jay to converse with the Jarvis Brain interactively in terminal.
"""

from __future__ import annotations

import sys
from core.brain import run_interactive_cli


def main() -> None:
    """Launch the interactive terminal runner."""
    run_interactive_cli()


if __name__ == "__main__":
    main()
