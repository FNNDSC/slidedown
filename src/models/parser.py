"""
Parser-specific data models

Type-safe structures for parser operations and return values.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..lib.parser import ASTNode


@dataclass
class DirectiveMatch:
    """
    Result of finding a directive pattern in source text

    Returned by Parser.directive_find() when a .directive{ pattern is located.
    Contains the directive name and its position in the source string.

    Attributes:
        name: The directive name (e.g., "slide", "title", "font-doom")
        position: Character position in source where the directive starts

    Example:
        For source ".slide{content}" at position 0:
        DirectiveMatch(name="slide", position=0)
    """
    name: str
    position: int


@dataclass
class ProcessedContent:
    """
    Result of recursively processing directive content

    Returned by Parser.content_processRecursive() after extracting nested
    directives and modifiers from a directive's content string.

    Attributes:
        content: Content string with nested directives replaced by placeholders
                 (e.g., "Welcome to \x00CHILD_0\x00!")
        children: List of ASTNodes for nested directives, indexed to match
                  placeholders (CHILD_0 → children[0])
        modifiers: Extracted modifier directives (.style{}, .class{}) as dict
                   (e.g., {"style": "color: red", "class": "highlight"})

    Example:
        Input content: ".style{color:red} Hello .bf{world}"
        Result: ProcessedContent(
            content="Hello \x00CHILD_0\x00",
            children=[ASTNode(directive="bf", content="world", ...)],
            modifiers={"style": "color:red"}
        )
    """
    content: str
    children: List['ASTNode']  # Forward reference for type checking
    modifiers: Dict[str, str]


@dataclass
class ExtractedModifiers:
    """
    Result of extracting modifier directives from content start

    Returned by Parser.modifiers_extract() after scanning for .style{} and
    .class{} directives at the beginning of content.

    Attributes:
        modifiers: Dict mapping modifier names to their values
                   (e.g., {"style": "background: black", "class": "special"})
        remaining: Content string with modifiers removed
                   (preserves whitespace if no modifiers found)

    Example:
        Input: ".style{font-size: 2em} .class{big} Content here"
        Result: ExtractedModifiers(
            modifiers={"style": "font-size: 2em", "class": "big"},
            remaining="Content here"
        )

        Input (no modifiers): "  Plain content"
        Result: ExtractedModifiers(
            modifiers={},
            remaining="  Plain content"  # Whitespace preserved
        )
    """
    modifiers: Dict[str, str]
    remaining: str
