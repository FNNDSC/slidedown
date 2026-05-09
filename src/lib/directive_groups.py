"""Focused directive registration groups."""

from __future__ import annotations

from typing import Protocol

from ..models.directives import DirectiveCategory, DirectiveSpec
from ..models.handlers import CompilerContext, DirectiveHandler, DirectiveNode


class DirectiveRegistrar(Protocol):
    """Minimal registry interface used by directive group modules."""

    def register(self, spec: DirectiveSpec) -> None: ...


def formattingDirectives_register(registry: DirectiveRegistrar) -> None:
    """Register HTML formatting directives."""
    formatting_specs = [
        ("bf", "strong", "Bold/strong text", [".bf{bold text}"]),
        ("em", "em", "Emphasized/italic text", [".em{italic text}"]),
        ("tt", "tt", "Teletype/monospace text", [".tt{monospace}"]),
        ("underline", "u", "Underlined text", [".underline{underlined}"]),
        ("div", "div", "Generic block container", [".div{block content}"]),
        ("span", "span", "Generic inline container", [".span{inline}"]),
    ]

    for name, tag, description, examples in formatting_specs:
        registry.register(
            DirectiveSpec(
                name=name,
                category=DirectiveCategory.FORMATTING,
                description=description,
                handler=_htmlWrapper_make(tag),
                examples=examples,
            )
        )

    registry.register(
        DirectiveSpec(
            name="flash",
            aliases=["blink"],
            category=DirectiveCategory.FORMATTING,
            description="Blinking text effect",
            handler=_htmlWrapper_make("span", "sl-blink"),
            examples=[".flash{blinking text}", ".blink{also blinking}"],
        )
    )

    heading_specs = [
        ("h1", "h1", "Heading level 1 (largest)", [".h1{Main Title}"]),
        ("h2", "h2", "Heading level 2", [".h2{Section Title}"]),
        ("h3", "h3", "Heading level 3", [".h3{Subsection Title}"]),
        ("h4", "h4", "Heading level 4", [".h4{Minor Heading}"]),
        ("h5", "h5", "Heading level 5", [".h5{Small Heading}"]),
        ("h6", "h6", "Heading level 6 (smallest)", [".h6{Tiny Heading}"]),
    ]

    for name, tag, description, examples in heading_specs:
        registry.register(
            DirectiveSpec(
                name=name,
                category=DirectiveCategory.FORMATTING,
                description=description,
                handler=_htmlWrapper_make(tag),
                examples=examples,
            )
        )


def modifierDirectives_register(registry: DirectiveRegistrar) -> None:
    """Register parser-extracted modifier directives."""
    modifier_specs = [
        (
            "style",
            "Inline CSS styles (parser-extracted modifier)",
            [".slide{.style{color: red} .body{Content}}"],
        ),
        (
            "class",
            "CSS class name (parser-extracted modifier)",
            [".slide{.class{special-slide} .body{Content}}"],
        ),
        (
            "syntax",
            "Programming language for .code{} (parser-extracted modifier)",
            [".code{.syntax{language=python} def foo(): pass}"],
        ),
        (
            "effect",
            "Bridge animation for LCARS theme",
            [".slide{.effect{histogram}}"],
        ),
    ]

    for name, description, examples in modifier_specs:
        registry.register(
            DirectiveSpec(
                name=name,
                category=DirectiveCategory.MODIFIER,
                description=description,
                handler=_modifier_handler,
                examples=examples,
            )
        )


def _htmlWrapper_make(
    tag: str,
    default_class: str | None = None,
) -> DirectiveHandler:
    """Create a handler that wraps node content in a simple HTML tag."""

    def handler(node: DirectiveNode, compiler: CompilerContext) -> str:
        style = node.modifiers.get("style", "")
        style_attr = f' style="{style}"' if style else ""
        user_class = node.modifiers.get("class", "")
        classes: list[str] = []
        if default_class:
            classes.append(default_class)
        if user_class:
            classes.append(user_class)

        class_attr = f' class="{" ".join(classes)}"' if classes else ""
        return f"<{tag}{class_attr}{style_attr}>{node.content}</{tag}>"

    return handler


def _modifier_handler(node: DirectiveNode, compiler: CompilerContext) -> str:
    """Return no HTML for parser-extracted modifiers."""
    return ""
