"""
Parser for .directive{} syntax

Transforms slidedown markup into an abstract syntax tree (AST).

The parser operates in two phases:
1. Scanning: Locate .directive{} patterns in source text
2. Processing: Extract content, handle nesting, create AST nodes

Key features:
- Recursive descent parsing for nested directives
- Placeholder substitution for children (\x00CHILD_N\x00)
- Modifier extraction (.style{}, .class{})
- Brace depth tracking for proper nesting
- Line number tracking for error reporting

Example:
    >>> parser = Parser(".slide{.title{Hello} .body{World}}")
    >>> nodes = parser.parse()
    >>> nodes[0].directive
    'slide'
    >>> nodes[0].children[0].directive
    'title'
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..models.parser import DirectiveMatch, ProcessedContent, ExtractedModifiers


@dataclass
class ASTNode:
    """
    Represents a node in the abstract syntax tree

    Each node corresponds to a single .directive{} in the source, containing
    its content, nested children, modifiers, and source location.

    Attributes:
        directive: Directive name (e.g., "slide", "title", "font-doom")
        modifiers: Extracted modifier directives as dict
                   (e.g., {"style": "color: red", "class": "highlight"})
        content: Content string with nested directives replaced by placeholders
                 (e.g., "Hello \x00CHILD_0\x00 world")
        children: Nested directive nodes, indexed to match placeholders
                  (CHILD_0 → children[0], CHILD_1 → children[1], etc.)
        line_number: Source line number where directive appears (for error reporting)

    Example:
        For source ".slide{.title{Hi} .body{There}}" at line 1:
        ASTNode(
            directive="slide",
            modifiers={},
            content="\x00CHILD_0\x00 \x00CHILD_1\x00",
            children=[
                ASTNode(directive="title", content="Hi", ...),
                ASTNode(directive="body", content="There", ...)
            ],
            line_number=1
        )
    """
    directive: str
    modifiers: Dict[str, str]
    content: str
    children: List['ASTNode']
    line_number: int


class Parser:
    """
    Parser for slidedown .directive{content} syntax

    Handles:
    - Nested directives
    - Modifiers (.style{}, .class{})
    - Mixed HTML and directive syntax
    - Error reporting with line numbers
    """

    def __init__(self, source: str, debug: bool = False):
        """
        Initialize parser with source text

        Args:
            source: Raw slidedown source text (.sd file contents)
            debug: Enable debug output for parser operations

        Attributes:
            source: Source text being parsed
            debug: Debug mode flag
            position: Current character position in source (for scanning)
            line_number: Current line number in source (for error reporting)
            ast: Accumulated list of parsed top-level nodes
            protected_code_blocks: Dict mapping placeholder IDs to raw .code{} content
        """
        self.source = source
        self.debug = debug
        self.position = 0
        self.line_number = 1
        self.ast: List[ASTNode] = []
        self.protected_code_blocks: Dict[int, str] = {}

    def codeblocks_protect(self) -> str:
        """
        Pre-process source to protect .code{} blocks from directive parsing

        Scans for .code{} directives and replaces them with placeholders to prevent
        nested directives inside code blocks from being parsed. The raw content is
        stored for later restoration during compilation.

        Returns:
            Modified source with .code{} blocks replaced by placeholders

        Example:
            Input: ".code{.syntax{language=python}\ndef foo(): pass\n}"
            Output: "\x00CODE_0\x00"
            Stores: protected_code_blocks[0] = ".syntax{language=python}\ndef foo(): pass\n"
        """
        result = []
        pos = 0
        code_id = 0

        while pos < len(self.source):
            # Look for .code{ directive
            match = re.match(r'\.code\{', self.source[pos:])
            if match:
                # Found .code{ - find matching closing brace
                brace_start = pos + match.end() - 1  # Position of opening {
                brace_end = self.brace_findMatching(brace_start)

                # Extract raw content (including .syntax{} modifier if present)
                raw_content = self.source[brace_start + 1:brace_end]

                # Store protected content
                self.protected_code_blocks[code_id] = raw_content

                # Replace with placeholder
                result.append(f'\x00CODE_{code_id}\x00')
                code_id += 1

                # Skip past this .code{} block
                pos = brace_end + 1
            else:
                # Regular character, keep it
                result.append(self.source[pos])
                pos += 1

        return ''.join(result)

    def parse(self) -> List[ASTNode]:
        """
        Parse source text into abstract syntax tree

        Main entry point for parsing. Scans source for top-level .directive{}
        patterns, processes each recursively, and returns a forest of AST trees.

        Returns:
            List of top-level ASTNode objects, one per top-level directive.
            Returns empty list for empty/whitespace-only source.

        Raises:
            SyntaxError: If source contains malformed directives (unmatched
                        braces, invalid syntax, etc.)

        Example:
            >>> parser = Parser(".slide{First}\\n.slide{Second}")
            >>> nodes = parser.parse()
            >>> len(nodes)
            2
            >>> nodes[0].directive
            'slide'
        """
        nodes = []

        # Pre-process: protect .code{} blocks from parsing
        self.source = self.codeblocks_protect()

        # Skip leading whitespace
        self.source = self.source.strip()
        if not self.source:
            return []

        self.position = 0
        self.line_number = 1

        while self.position < len(self.source):
            # Skip whitespace
            while self.position < len(self.source) and self.source[self.position].isspace():
                if self.source[self.position] == '\n':
                    self.line_number += 1
                self.position += 1

            if self.position >= len(self.source):
                break

            # Find next directive
            match = self.directive_find()
            if not match:
                break

            directive_name = match.name
            directive_pos = match.position

            # Find opening brace
            brace_pos = self.source.find('{', directive_pos)
            if brace_pos == -1:
                self.error(f"Expected '{{' after directive '.{directive_name}'")

            # Find matching closing brace
            try:
                close_brace_pos = self.brace_findMatching(brace_pos)
            except SyntaxError:
                raise

            # Extract content
            content = self.source[brace_pos + 1:close_brace_pos]

            # Process content recursively
            processed = self.content_processRecursive(content, self.line_number)

            # Create AST node
            node = ASTNode(
                directive=directive_name,
                modifiers=processed.modifiers,
                content=processed.content,
                children=processed.children,
                line_number=self.line_number
            )
            nodes.append(node)

            # Move position past this directive
            self.position = close_brace_pos + 1

        return nodes

    def directive_find(self) -> Optional[DirectiveMatch]:
        """
        Find next .directive{ pattern in source from current position

        Scans forward from self.position looking for .directive{ pattern.
        Supports simple names (e.g., "slide") and hyphenated names (e.g.,
        "font-doom", "my-custom-directive").

        Returns:
            DirectiveMatch with name and position, or None if no more directives

        Example:
            For source ".slide{content}" at position 0:
            Returns DirectiveMatch(name="slide", position=0)

            For source "text .title{hi}" at position 0:
            Returns DirectiveMatch(name="title", position=5)
        """
        pattern = r'\.(\w+(?:-\w+)*)\{'
        match = re.search(pattern, self.source[self.position:])
        if match:
            directive = match.group(1)
            pos = self.position + match.start()
            return DirectiveMatch(name=directive, position=pos)
        return None

    def brace_findMatching(self, start_pos: int) -> int:
        """
        Find matching closing brace using depth tracking

        Scans forward from opening brace, tracking nesting depth. Increments
        depth on '{', decrements on '}'. Returns position when depth reaches 0.

        Args:
            start_pos: Character position of opening '{' in source

        Returns:
            Character position of matching closing '}'

        Raises:
            SyntaxError: If EOF reached before finding matching brace (depth != 0)

        Example:
            For source ".code{function() { return {}; }}" at position 5 (opening brace):
            Returns 32 (position of final closing brace)

            Depth tracking: {1 function() {2 return {3}2; }1}0
        """
        depth = 1
        pos = start_pos + 1

        while pos < len(self.source) and depth > 0:
            if self.source[pos] == '{':
                depth += 1
            elif self.source[pos] == '}':
                depth -= 1
            pos += 1

        if depth != 0:
            raise SyntaxError(
                f"Unmatched brace at line {self.line_number}, position {start_pos}"
            )

        return pos - 1

    def content_processRecursive(
        self, content: str, line_num: int
    ) -> ProcessedContent:
        """
        Recursively process directive content to extract nested directives

        Core parsing logic that transforms raw content into structured form:
        1. Extract modifiers (.style{}, .class{}) from content start
        2. Find nested .directive{} patterns
        3. Recursively process each nested directive's content
        4. Replace nested directives with placeholders (\x00CHILD_N\x00)
        5. Build list of child ASTNodes

        Args:
            content: Raw content string from inside directive braces
            line_num: Source line number (for error reporting in nested directives)

        Returns:
            ProcessedContent containing:
                - content: String with nested directives replaced by placeholders
                - children: List of child ASTNodes (indexed to match placeholders)
                - modifiers: Extracted modifier directives dict

        Example:
            Input: ".style{color:red} Hello .bf{world}"
            Output: ProcessedContent(
                content="Hello \x00CHILD_0\x00",
                children=[ASTNode(directive="bf", content="world", ...)],
                modifiers={"style": "color:red"}
            )
        """
        from ..config import appsettings

        # Extract modifiers first
        extracted = self.modifiers_extract(content)
        modifiers = extracted.modifiers
        remaining_content = extracted.remaining

        # Find and replace nested directives with placeholders
        children = []
        processed = remaining_content
        child_index = 0

        # Scan for nested directives
        pos = 0
        while pos < len(processed):
            # Look for .directive{ pattern
            match = re.search(r'\.(\w+(?:-\w+)*)\{', processed[pos:])
            if not match:
                break

            directive_name = match.group(1)
            match_start = pos + match.start()
            brace_start = pos + match.end() - 1  # Position of {

            # Find matching closing brace
            depth = 1
            brace_pos = brace_start + 1
            while brace_pos < len(processed) and depth > 0:
                if processed[brace_pos] == '{':
                    depth += 1
                elif processed[brace_pos] == '}':
                    depth -= 1
                brace_pos += 1

            if depth != 0:
                raise SyntaxError(f"Unmatched brace in nested directive '.{directive_name}' at line {line_num}")

            brace_end = brace_pos - 1  # Position of }

            # Extract nested content
            nested_content = processed[brace_start + 1:brace_end]

            # Recursively process nested content
            processed_child = self.content_processRecursive(nested_content, line_num)

            # Create child node
            child = ASTNode(
                directive=directive_name,
                modifiers=processed_child.modifiers,
                content=processed_child.content,
                children=processed_child.children,
                line_number=line_num
            )
            children.append(child)

            # Replace directive with placeholder
            placeholder = appsettings.placeHolder_make(child_index)
            processed = processed[:match_start] + placeholder + processed[brace_pos:]

            # Adjust position (placeholder might be different length than original)
            pos = match_start + len(placeholder)
            child_index += 1

        return ProcessedContent(
            content=processed,
            children=children,
            modifiers=modifiers
        )

    def modifiers_extract(self, content: str) -> ExtractedModifiers:
        """
        Extract modifier directives from content beginning

        Scans for .style{}, .class{}, and .syntax{} directives at the start of content
        (after optional leading whitespace). Extracts their values into a dict
        and returns the remaining content with modifiers removed.

        Note: If no modifiers are found, returns original content unchanged
        (preserves leading whitespace).

        Args:
            content: Raw content string to scan for modifiers

        Returns:
            ExtractedModifiers containing:
                - modifiers: Dict of modifier names to values
                - remaining: Content with modifiers stripped

        Example:
            Input: ".style{color: red} .class{big} .syntax{language=python} Content"
            Output: ExtractedModifiers(
                modifiers={"style": "color: red", "class": "big", "syntax": "language=python"},
                remaining="Content"
            )

            Input: "  Plain text"
            Output: ExtractedModifiers(modifiers={}, remaining="  Plain text")
        """
        modifiers = {}
        pos = 0

        # Skip leading whitespace to find modifiers
        ws_start = pos
        while pos < len(content) and content[pos].isspace():
            pos += 1

        # Check if there's a modifier at this position
        first_modifier_found = False

        # Look for .style{}, .class{}, and .syntax{} at the start
        while pos < len(content):
            match = re.match(r'^\.((style|class|syntax))\{', content[pos:])
            if not match:
                break

            # Found a modifier - mark that we should skip leading whitespace
            if not first_modifier_found:
                first_modifier_found = True

            modifier_name = match.group(1)
            brace_start = pos + match.end() - 1

            # Find matching closing brace
            depth = 1
            brace_pos = brace_start + 1
            while brace_pos < len(content) and depth > 0:
                if content[brace_pos] == '{':
                    depth += 1
                elif content[brace_pos] == '}':
                    depth -= 1
                brace_pos += 1

            if depth != 0:
                raise SyntaxError(f"Unmatched brace in modifier '.{modifier_name}'")

            # Extract modifier value
            modifier_value = content[brace_start + 1:brace_pos - 1]

            # Special handling for .style{} - extract align= if present
            if modifier_name == 'style':
                align_match = re.search(r'align\s*=\s*(\w+)', modifier_value)
                if align_match:
                    # Extract align value as separate modifier
                    modifiers['align'] = align_match.group(1)
                    # Remove align= from style value
                    style_value = re.sub(r'align\s*=\s*\w+\s*;?\s*', '', modifier_value).strip()
                    # Remove trailing semicolon if it's the only thing left
                    style_value = style_value.rstrip(';').strip()
                    if style_value:
                        modifiers[modifier_name] = style_value
                    # Don't add empty style modifier
                else:
                    modifiers[modifier_name] = modifier_value
            else:
                modifiers[modifier_name] = modifier_value

            # Move past this modifier
            pos = brace_pos

            # Skip whitespace after modifier
            while pos < len(content) and content[pos].isspace():
                pos += 1

        # If no modifiers found, return original content
        if not first_modifier_found:
            return ExtractedModifiers(modifiers=modifiers, remaining=content)

        # Return content with modifiers removed
        return ExtractedModifiers(modifiers=modifiers, remaining=content[pos:])

    def error(self, message: str) -> None:
        """
        Report parser error with source context

        Raises SyntaxError with detailed error message including:
        - Custom error message
        - Line number and character position
        - Source context (±40 characters around error)
        - Caret indicator pointing to error position

        Args:
            message: Human-readable error description

        Raises:
            SyntaxError: Always (this is an error reporting function)

        Example output:
            SyntaxError:
            Expected '{' after directive '.slide'
            Line 3, position 42
            Context: ...text .slide content more text...
                                   ^
        """
        context_start = max(0, self.position - 40)
        context_end = min(len(self.source), self.position + 40)
        context = self.source[context_start:context_end]

        raise SyntaxError(
            f"\n{message}\n"
            f"Line {self.line_number}, position {self.position}\n"
            f"Context: ...{context}...\n"
            f"         {' ' * (self.position - context_start)}^"
        )
