#!/usr/bin/env python3
"""
slidedown - Text-first presentation compiler

A LaTeX-inspired markup compiler for creating interactive HTML presentations
from plain text source files.

As an aside, this codebase leverages the ChRIS "plugin" concept/pattern as
general purpose python app development framework.

Philosophy:
    - Text-first: Source files remain human-readable without compilation
    - Directive markup: .directive{content} syntax for transformations
    - Single-file workflow: One .sd source → one standalone HTML output
    - HTML-compatible: Mix directive markup with raw HTML as needed

Key Features:
    - Typewriter effects for character-by-character reveal
    - Progressive bullet reveals (.o{} snippets)
    - ASCII art integration (figlet fonts, cowsay)
    - Responsive viewport-based sizing
    - Standalone output (no server dependencies)

Usage:
    slidedown inputdir/ outputdir/ --inputFile slides.sd

    The compiled presentation will be written to outputdir/ as a
    self-contained HTML file with embedded CSS/JS.

Examples:
    # Basic compilation
    slidedown . output/ --inputFile presentation.sd

    # With custom assets and output subdirectory
    slidedown . output/ --inputFile slides.sd --assetsDir custom_theme/ --outputSubdir presentation/

    # Verbose output
    slidedown . output/ --inputFile slides.sd -vv
"""

import sys
from pathlib import Path
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter

from chris_plugin import chris_plugin
from .lib import Parser, Compiler, __version__, LOG, state_connectToLogger
from .models import ProgramState, pipeline


DISPLAY_TITLE = r"""
       _ _     _          _
   ___| (_) __| | ___  __| | _____      ___ __
  / __| | |/ _` |/ _ \/ _` |/ _ \ \ /\ / / '_ \
  \__ \ | | (_| |  __/ (_| | (_) \ V  V /| | | |
  |___/_|_|\__,_|\___|\__,_|\___/ \_/\_/ |_| |_|

  Text-first presentation compiler
"""

# Define CLI arguments
parser = ArgumentParser(
    description="slidedown - Text-first presentation compiler with behavioral markup",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "--inputFile", required=True, type=str, help="Input slidedown (.sd) file (relative to inputdir)"
)

parser.add_argument(
    "--assetsDir",
    default=None,
    type=str,
    help="Directory containing runtime assets (css/js/html). Defaults to package assets/ dir",
)

parser.add_argument(
    "--outputSubdir",
    default=".",
    type=str,
    help="Subdirectory within outputdir for the compiled slideshow",
)

parser.add_argument(
    "-v",
    "--verbosity",
    action="count",
    default=1,
    help="Increase output verbosity (can be repeated: -v, -vv, -vvv)",
)

parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")


def env_check(inputstate: ProgramState) -> ProgramState:
    """
    Validate environment and resolve all file paths.

    Verifies that the input file and assets directory exist, then creates
    the output directory structure.

    Args:
        inputstate: Initial program state with CLI options

    Returns:
        ProgramState with added fields:
            - inputSourceFile: Resolved path to .sd input file
            - assetsInputdir: Resolved path to assets directory
            - htmlOutputdir: Created output directory path
            - envOK: True if environment is valid

    Exits:
        1 if input file or assets directory not found
    """

    state = inputstate.copy()

    if state.verbosity >= 2:
        LOG(DISPLAY_TITLE, level=2)

    LOG("Checking environment...", level=2)

    # Resolve paths
    input_file = state.inputdir / state.inputFile

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        state.envOK = False
        sys.exit(1)

    state.inputSourceFile = input_file
    LOG(f"Input file: {input_file}", level=2)

    # Determine assets directory
    if state.assetsDir:
        state.assetsInputdir = Path(state.assetsDir)
    else:
        # Use package default
        package_root = Path(__file__).parent.parent
        state.assetsInputdir = package_root / "assets"

    if not state.assetsInputdir.exists():
        print(f"Error: Assets directory not found: {state.assetsInputdir}", file=sys.stderr)
        print("Specify with --assetsDir or ensure package is properly installed", file=sys.stderr)
        state.envOK = False
        sys.exit(1)

    LOG(f"Assets directory: {state.assetsInputdir}", level=2)

    # Determine output subdirectory
    state.htmlOutputdir = state.outputdir / state.outputSubdir
    state.htmlOutputdir.mkdir(parents=True, exist_ok=True)
    LOG(f"Output directory: {state.htmlOutputdir}", level=2)

    state.envOK = True
    return state


def source_parse(inputstate: ProgramState) -> ProgramState:
    """
    Read and parse slidedown source file into abstract syntax tree.

    Reads the .sd file from disk and parses it using the slidedown Parser
    to produce an AST representing the document structure.

    Args:
        inputstate: Program state with inputSourceFile path set

    Returns:
        ProgramState with added field:
            - parsedSource: List[ASTNode] representing the parsed document

    Exits:
        1 if file read fails or parsing encounters syntax errors
    """

    state = inputstate.copy()

    LOG("Reading source file...", level=1)

    try:
        source = state.inputSourceFile.read_text(encoding="utf-8")
        LOG(f"Read {len(source)} characters from {state.inputSourceFile.name}", level=2)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    LOG("Parsing source into AST...", level=1)
    try:
        slidedown_parser = Parser(source, debug=(state.verbosity >= 3))
        state.parsedSource = slidedown_parser.parse()
        LOG(f"Parsed {len(state.parsedSource)} top-level nodes", level=2)
    except SyntaxError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    return state


def html_compile(inputstate: ProgramState) -> ProgramState:
    """
    Compile abstract syntax tree to standalone HTML presentation.

    Takes the parsed AST and compiles it to HTML using the Compiler,
    applying behaviors, injecting assets, and generating the final
    self-contained presentation file.

    Args:
        inputstate: Program state with parsedSource AST

    Returns:
        ProgramState with added field:
            - compileResult: Dict containing:
                - status: bool (compilation success)
                - output_file: str (path to generated index.html)
                - slide_count: int (number of slides compiled)

    Exits:
        1 if parsedSource is None or compilation fails
    """

    state = inputstate.copy()

    LOG("Compiling AST to HTML...", level=1)

    if not state.parsedSource:
        print("Error: No parsed source available", file=sys.stderr)
        sys.exit(1)

    try:
        compiler = Compiler(
            ast=state.parsedSource,
            output_dir=str(state.htmlOutputdir),
            assets_dir=str(state.assetsInputdir),
            verbosity=state.verbosity,
        )
        state.compileResult = compiler.compile()
        LOG(f"Compilation complete: {state.compileResult['slide_count']} slides", level=2)
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        if state.verbosity >= 3:
            import traceback

            traceback.print_exc()
        sys.exit(1)

    return state


def results_report(inputstate: ProgramState) -> ProgramState:
    """
    Display compilation results and usage instructions to user.

    Outputs a summary of the compilation including output file path,
    slide count, and instructions for viewing the presentation.

    Args:
        inputstate: Program state with compileResult populated

    Returns:
        ProgramState unchanged (terminal pipeline stage)

    Exits:
        1 if compileResult is None
    """
    state: ProgramState = inputstate.copy()
    if not state.compileResult:
        print("Error: Compilation failed", file=sys.stderr)
        sys.exit(1)

    if state.verbosity >= 1:
        LOG("\n✓ Compilation successful!", level=1)
        LOG(f"  Output: {state.compileResult['output_file']}", level=1)
        LOG(f"  Slides: {state.compileResult['slide_count']}", level=1)
        LOG("\nTo view:", level=1)
        LOG(f"  cd {state.htmlOutputdir}", level=1)
        LOG("  python3 -m http.server 8000", level=1)
    return state


@chris_plugin(
    parser=parser,
    title="slidedown - Text-first presentation compiler",
    category="Visualization",
    min_memory_limit="100Mi",
    min_cpu_limit="500m",
)
def main(options: Namespace, inputdir: Path, outputdir: Path):
    """
    Main entry point - compile slidedown presentation from .sd source to HTML.

    Orchestrates the full compilation pipeline:
        1. env_check: Validate paths and environment
        2. source_parse: Read and parse .sd file to AST
        3. html_compile: Compile AST to HTML with assets
        4. results_report: Display results to user

    Args:
        options: CLI arguments from argparse
            - inputFile: str - Input .sd filename
            - assetsDir: Optional[str] - Custom assets directory
            - outputSubdir: str - Output subdirectory name
            - verbosity: int - Logging verbosity level (1-3)
        inputdir: Directory containing slidedown source files
        outputdir: Directory where compiled presentation will be written

    Note:
        This function is wrapped by @chris_plugin which handles CLI
        argument parsing and invokes this function with parsed values.
    """

    state: ProgramState = ProgramState.state_createFromNamespace(
        options=options, inputdir=inputdir, outputdir=outputdir
    )

    # Connect state to logger for entire pipeline
    state_connectToLogger(state)

    # Execute compilation pipeline
    pipeline(state, env_check, source_parse, html_compile, results_report)


if __name__ == "__main__":
    main()  # type: ignore  # @chris_plugin decorator transforms signature
