"""
slidedown - Text-first presentation compiler

A LaTeX-inspired markup system for creating interactive HTML presentations.
"""

__version__ = "1.0.0"
__author__ = "Rudolph Pienaar"
__email__ = "rudolph.pienaar@gmail.com"

from .parser import Parser
from .compiler import Compiler
from .directives import DirectiveRegistry
from .log import LOG, state_connectToLogger

__all__ = ["Parser", "Compiler", "DirectiveRegistry", "LOG", "state_connectToLogger", "__version__"]
