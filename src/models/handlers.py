"""Directive handler protocols."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TypeAlias

from .compiler import ConfigValue, PresentationMetaConfig, ThemeLike


class DirectiveNode(Protocol):
    """AST node attributes consumed by directive handlers."""

    directive: str
    modifiers: dict[str, str]
    content: str
    children: Sequence[DirectiveNode]
    line_number: int


class CompilerContext(Protocol):
    """Compiler attributes consumed by directive handlers."""

    input_dir: Path
    meta_config: PresentationMetaConfig
    protected_code_blocks: dict[int, str]
    escaped_sequences: dict[int, str]
    slide_count: int
    snippet_counters: dict[int, int]
    theme: ThemeLike
    typewriter_counters: dict[int, int]

    def ast_compile(self, nodes: list) -> str: ...

    def config_getMerged(
        self, key: str, default: ConfigValue = None
    ) -> ConfigValue: ...

    def watermarks_generate(self) -> str: ...


DirectiveHandler: TypeAlias = Callable[[DirectiveNode, CompilerContext], str]
