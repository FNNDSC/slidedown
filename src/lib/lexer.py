"""
Custom Pygments lexer for slidedown syntax highlighting

Provides syntax highlighting for .directive{} markup when displaying
slidedown source code in presentations.

Token types:
- Name.Tag: Directive names (e.g., .slide, .title, .bf)
- Punctuation: Braces and dots
- String: Content inside directives
- Name.Attribute: Modifiers (e.g., .style{}, .syntax{})
- Literal: Modifier values (e.g., language=python)
"""

from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import (
    Text,
    Punctuation,
    Name,
    String,
    Keyword,
    Literal,
    Comment,
    Generic,
    Number,
)


class SlidedownLexer(RegexLexer):
    """
    Lexer for slidedown markup language

    Highlights .directive{} syntax with proper nesting support.

    Example:
        .slide{.title{Hello} .body{World}}

    Tokens:
        .slide → Name.Tag
        { → Punctuation
        .title → Name.Tag
        Hello → String
        } → Punctuation
    """

    name = 'Slidedown'
    aliases = ['slidedown', 'sd']
    filenames = ['*.sd']

    tokens = {
        'root': [
            # HTML comments
            (r'<!--.*?-->', Comment),

            # HTML tags (pass through as-is)
            (r'<[^>]+>', Name.Builtin),

            # .comment{} directive - special handling
            (r'(\.)(comment)(\{)', bygroups(Punctuation, Name.Tag, Punctuation), 'comment'),

            # Structural directives (blue/cyan) - Keyword.Declaration
            (r'(\.)((slide|title|body))(\{)?',
             bygroups(Punctuation, Keyword.Declaration, None, Punctuation)),

            # Reserved modifiers (purple) - Name.Decorator
            (r'(\.)((style|class|syntax))(\{)?',
             bygroups(Punctuation, Name.Decorator, None, Punctuation)),

            # Behavioral/Effect directives (yellow/orange) - Literal.Number
            (r'(\.)((o|typewriter|column))(\{)?',
             bygroups(Punctuation, Literal.Number, None, Punctuation)),

            # Formatting directives (green) - Name.Function
            (r'(\.)((bf|em|tt|code|underline|h1|h2|h3|h4|h5|h6))(\{)?',
             bygroups(Punctuation, Name.Function, None, Punctuation)),

            # Transform directives (orange) - Number (font-*, cowpy-*)
            (r'(\.)((font|cowpy)-[\w-]+)(\{)?',
             bygroups(Punctuation, Number, None, Punctuation)),

            # Other directives (fallback - current pink)
            (r'(\.)([a-zA-Z_][\w-]*)', bygroups(Punctuation, Name.Tag)),

            # Opening brace
            (r'\{', Punctuation, 'content'),

            # Closing brace (shouldn't appear in root, but handle gracefully)
            (r'\}', Punctuation),

            # Everything else is text
            (r'[^.<{}]+', Text),
            (r'.', Text),
        ],

        'comment': [
            # Inside .comment{} - everything is comment text until closing brace
            (r'\}', Punctuation, '#pop'),
            (r'[^}]+', Comment),
            (r'.', Comment),
        ],

        'content': [
            # HTML comments inside content
            (r'<!--.*?-->', Comment),

            # .comment{} directive inside content
            (r'(\.)(comment)(\{)', bygroups(Punctuation, Name.Tag, Punctuation), 'comment'),

            # Structural directives (blue/cyan)
            (r'(\.)((slide|title|body))(\{)?',
             bygroups(Punctuation, Keyword.Declaration, None, Punctuation)),

            # Reserved modifiers (purple)
            (r'(\.)((style|class|syntax))(\{)?',
             bygroups(Punctuation, Name.Decorator, None, Punctuation)),

            # Behavioral/Effect directives (yellow/orange)
            (r'(\.)((o|typewriter|column))(\{)?',
             bygroups(Punctuation, Literal.Number, None, Punctuation)),

            # Formatting directives (green)
            (r'(\.)((bf|em|tt|code|underline|h1|h2|h3|h4|h5|h6))(\{)?',
             bygroups(Punctuation, Name.Function, None, Punctuation)),

            # Transform directives (orange)
            (r'(\.)((font|cowpy)-[\w-]+)(\{)?',
             bygroups(Punctuation, Number, None, Punctuation)),

            # Other nested directives (fallback)
            (r'(\.)([a-zA-Z_][\w-]*)', bygroups(Punctuation, Name.Tag)),

            # Opening brace (allows nesting)
            (r'\{', Punctuation, 'content'),

            # Closing brace (pop back to previous state)
            (r'\}', Punctuation, '#pop'),

            # HTML tags inside content
            (r'<[^>]+>', Name.Builtin),

            # Modifier key=value patterns (e.g., language=python, style=color:red)
            (r'([a-zA-Z_][\w-]*)(=)([^\s}]+)',
             bygroups(Name.Attribute, Punctuation, Literal.String)),

            # Regular text content
            (r'[^.<{}]+', String),
            (r'.', String),
        ],
    }


def get_lexer() -> SlidedownLexer:
    """
    Get the SlidedownLexer instance

    Returns:
        SlidedownLexer instance ready for use with Pygments
    """
    return SlidedownLexer()
