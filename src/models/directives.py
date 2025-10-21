"""
Directive specification and metadata models

Defines the structure and categories of slidedown directives for
validation, documentation generation, and registry management.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set


class DirectiveCategory(Enum):
    """
    Categories of slidedown directives

    Used for organization, documentation generation, and validation.
    """
    STRUCTURAL = "structural"    # .slide{}, .body{}, .title{}
    FORMATTING = "formatting"    # .bf{}, .em{}, .code{}
    LAYOUT = "layout"           # .column{} (future)
    EFFECT = "effect"           # .typewriter{}, .o{}
    TRANSFORM = "transform"     # .font-*, .cowpy-*
    MODIFIER = "modifier"       # .style{}, .class{} (reserved)


@dataclass
class DirectiveSpec:
    """
    Specification for a slidedown directive

    Defines metadata, validation rules, and handler for a directive.
    Used by DirectiveRegistry to manage available directives.

    Attributes:
        name: Directive name (without leading dot)
        category: Category for organization
        description: Human-readable description
        handler: Compilation function (node, compiler) -> str
        requires_children: Whether directive must have child nodes
        allows_nesting: Whether directive can be nested inside others
        is_wildcard: Whether directive matches patterns (e.g., font-*)
        examples: Example usage strings
        aliases: Alternative names for the directive
    """
    name: str
    category: DirectiveCategory
    description: str
    handler: Callable
    requires_children: bool = False
    allows_nesting: bool = True
    is_wildcard: bool = False
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    def matches(self, directive_name: str) -> bool:
        """
        Check if this spec matches a directive name

        Handles wildcards (e.g., 'font-*' matches 'font-doom')

        Args:
            directive_name: Name to check

        Returns:
            True if this spec handles the directive
        """
        # Direct match
        if self.name == directive_name:
            return True

        # Check aliases
        if directive_name in self.aliases:
            return True

        # Wildcard match
        if self.is_wildcard:
            # Extract prefix (e.g., 'font-*' -> 'font-')
            if '-' in self.name:
                prefix = self.name.rsplit('-', 1)[0] + '-'
                if directive_name.startswith(prefix):
                    return True

        return False


# Reserved directives that are handled specially by the parser
RESERVED_DIRECTIVES: Set[str] = {
    'style',   # .style{css} - extracted as modifier
    'class',   # .class{classname} - extracted as modifier
    'syntax',  # .syntax{language=X} - extracted as modifier for .code{}
}


def reserved_is(directive_name: str) -> bool:
    """Check if a directive name is reserved"""
    return directive_name in RESERVED_DIRECTIVES
