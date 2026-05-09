"""
Centralized logging using Loguru with context-aware verbosity.

This module provides a LOG() function that respects the current ProgramState's
verbosity level without requiring explicit state passing.

Features:
- Context-aware logging tied to ProgramState verbosity
- Rich formatting with timestamps, colors, and metadata
- Thread-safe using contextvars
- Works throughout lib modules without passing state

Usage:
    from lib.log import LOG, state_connectToLogger

    # At start of pipeline function:
    state_connectToLogger(state)

    # Anywhere in that context:
    LOG("This message appears if verbosity >= 1", level=1)
    LOG("Debug details appear if verbosity >= 2", level=2)
    LOG("Verbose trace appears if verbosity >= 3", level=3)
"""

import sys
from contextvars import ContextVar
from typing import Any

from loguru import logger

# Context variable to hold current ProgramState
_program_state: ContextVar[Any | None] = ContextVar(
    "program_state", default=None
)

# Configure loguru with slidedown-specific format
logger_format = (
    "<green>{time:HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<cyan>{function: <20}</cyan> @ "
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)

logger.remove()  # Remove default handler
logger.add(sys.stderr, format=logger_format, level="DEBUG")


def state_connectToLogger(state: Any) -> None:
    """
    Connect a ProgramState to the logging context.

    Call this at the start of each pipeline function to make the state's
    verbosity setting available to LOG() calls throughout that context.

    Args:
        state: ProgramState instance with verbosity attribute

    Example:
        def source_parse(inputstate: ProgramState) -> ProgramState:
            state = inputstate.copy()
            state_connectToLogger(state)
            LOG("Starting parse...", level=1)
            # ...
    """
    _program_state.set(state)


def LOG(message: str, level: int = 1, **kwargs: Any) -> None:
    """
    Log message if current state's verbosity allows.

    Args:
        message: Log message to display
        level: Minimum verbosity level required (1=normal, 2=verbose, 3=debug)
        **kwargs: Additional loguru metadata.

    Verbosity levels:
        1 = Normal output (default)
        2 = Verbose (-v)
        3 = Debug (-vv or higher)

    Example:
        LOG("File read successfully", level=1)
        LOG("Parsing 42 AST nodes", level=2)
        LOG("Token at position 1337: .slide{", level=3)
    """
    state: Any | None = _program_state.get()

    if state and hasattr(state, "verbosity") and state.verbosity >= level:
        # depth=1 attributes records to LOG() callers.
        logger.opt(depth=1).debug(message, **kwargs)
