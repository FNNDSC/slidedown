"""
Models package for slidedown

Contains data structures and type definitions for the compilation pipeline.
"""

from .compiler import CompileResult, PresentationMetaConfig
from .directives import RESERVED_DIRECTIVES, DirectiveCategory, DirectiveSpec
from .parser import DirectiveMatch, ExtractedModifiers, ProcessedContent
from .state import ProgramState, pipeline

__all__ = [
    "ProgramState",
    "pipeline",
    "DirectiveSpec",
    "DirectiveCategory",
    "CompileResult",
    "PresentationMetaConfig",
    "RESERVED_DIRECTIVES",
    "DirectiveMatch",
    "ProcessedContent",
    "ExtractedModifiers",
]
