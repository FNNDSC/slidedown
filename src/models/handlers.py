"""Directive handler protocols."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TypeAlias

from .compiler import (
    ConfigValue,
    PlaceholderMap,
    PresentationMetaConfig,
    SlideCounters,
    ThemeLike,
)
from .parser import Modifiers


class DirectiveNode(Protocol):
    """AST node attributes consumed by directive handlers."""

    directive: str
    modifiers: Modifiers
    content: str
    children: Sequence[DirectiveNode]
    line_number: int


class CompilerContext(Protocol):
    """Compiler attributes consumed by directive handlers."""

    input_dir: Path
    meta_config: PresentationMetaConfig
    protected_code_blocks: PlaceholderMap
    escaped_sequences: PlaceholderMap
    slide_count: int
    snippet_counters: SlideCounters
    theme: ThemeLike
    typewriter_counters: SlideCounters

    def ast_compile(self, nodes: list) -> str: ...

    def config_getMerged(
        self, key: str, default: ConfigValue = None
    ) -> ConfigValue: ...

    def watermarks_generate(self) -> str: ...


DirectiveHandler: TypeAlias = Callable[[DirectiveNode, CompilerContext], str]
