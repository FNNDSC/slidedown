"""
Program state model and pipeline helper

Defines ProgramState dataclass for the functional pipeline pattern and
the pipeline() helper for composing transformation stages.
"""

from pathlib import Path
from argparse import Namespace
from typing import Any, Optional, Type, TypeVar, List, Dict, Callable, TYPE_CHECKING
from dataclasses import dataclass, field

# Forward reference for type hint - avoid circular import
if TYPE_CHECKING:
    from ..lib.parser import ASTNode


PS = TypeVar("PS", bound="ProgramState")


@dataclass
class ProgramState:
    """
    Central state container for the compilation pipeline (state bus pattern).

    This dataclass carries all program state through the functional pipeline,
    with each stage adding new fields as the compilation progresses.

    Pipeline stages and their state additions:
        - Initial: inputdir, outputdir, verbosity, inputFile, assetsDir, outputSubdir
        - env_check: inputSourceFile, assetsInputdir, htmlOutputdir, envOK
        - source_parse: parsedSource
        - html_compile: compileResult
        - results_report: (no additions, terminal stage)

    Attributes:
        inputdir: Directory containing source .sd file
        outputdir: Base output directory for compiled files
        verbosity: Logging verbosity level (1-3)
        inputFile: Input .sd filename (relative to inputdir)
        assetsDir: Optional custom assets directory path
        outputSubdir: Subdirectory within outputdir for output
        envOK: Environment validation passed
        inputSourceFile: Resolved path to input .sd file
        assetsInputdir: Resolved path to assets directory
        htmlOutputdir: Final output directory (outputdir + outputSubdir)
        parsedSource: Parsed AST from source file
        compileResult: Compilation results (output_file, slide_count, status)
    """

    # CLI arguments
    inputdir: Optional[Path] = field(default=None)
    outputdir: Optional[Path] = field(default=None)
    verbosity: int = field(default=1)
    inputFile: str = field(default="")
    assetsDir: Optional[str] = field(default=None)
    outputSubdir: str = field(default=".")

    # Pipeline state
    envOK: bool = field(default=False)
    inputSourceFile: Path = field(default=Path("/"))
    assetsInputdir: Path = field(default=Path("/"))
    htmlOutputdir: Path = field(default=Path("/"))
    parsedSource: Optional[List[Any]] = field(default=None)  # List[ASTNode] at runtime
    compileResult: Optional[Dict] = field(default=None)

    @classmethod
    def state_createFromNamespace(
        cls: Type["ProgramState"], options: Namespace, inputdir: Path, outputdir: Path
    ) -> "ProgramState":
        """
        Create ProgramState from argparse Namespace and directory paths.

        Merges CLI options with explicitly provided directories to create
        the initial program state for the compilation pipeline.

        Args:
            options: Parsed CLI arguments (inputFile, assetsDir, etc.)
            inputdir: Directory containing source files
            outputdir: Directory for compilation output

        Returns:
            ProgramState instance with all CLI options as attributes
        """
        # Get the dictionary of all attributes from the Namespace
        options_dict = vars(options)

        # Get the set of valid field names for ProgramState
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cls)}

        # Filter options_dict to only include fields that exist in ProgramState
        filtered_options = {k: v for k, v in options_dict.items() if k in valid_fields}

        # Merge the filtered CLI options with the explicitly defined arguments.
        # This will override any defaults set in the dataclass.
        merged_args = {**filtered_options, "inputdir": inputdir, "outputdir": outputdir}

        # Instantiate the dataclass by unpacking the merged dictionary.
        return cls(**merged_args)

    def copy(self: PS) -> PS:
        """
        Creates a shallow copy of the ProgramState instance.

        Returns:
            A new ProgramState instance.
        """
        return type(self)(**self.__dict__)


def pipeline(
    initial_state: ProgramState, *stages: Callable[[ProgramState], ProgramState]
) -> ProgramState:
    """
    Execute a functional pipeline of state transformations.

    Each stage is a function (ProgramState) -> ProgramState that receives
    the output of the previous stage and returns a new state.

    Args:
        initial_state: Starting ProgramState
        *stages: Variable number of stage functions to execute in order

    Returns:
        Final ProgramState after all transformations

    Example:
        final_state = pipeline(
            initial_state,
            env_check,
            source_parse,
            html_compile,
            results_report
        )

    This is equivalent to:
        results_report(html_compile(source_parse(env_check(initial_state))))

    But reads left-to-right instead of inside-out.
    """
    from functools import reduce
    return reduce(lambda state, stage: stage(state), stages, initial_state)
