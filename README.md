```slidedown
.meta{
  title: "Slidedown - Text-first Presentation Compiler"
}

.slide{
  .title{SLIDEDOWN}
  .body{
    .font-standard{SLIDEDOWN}

    Text-first presentation compiler with behavioral markup

    .bf{📊 View as Interactive Presentation:}
    https://fnndsc.github.io/slidedown/readme-presentation/

    .o{Documentation: docs/}
    .o{Examples: examples/}
  }
}

.slide{
  .title{What is slidedown?}
  .body{
    Do you like text? Have you ever wished that text was the
    basic substrate for compelling slideshows that are self
    contained and run in a browser?

    slidedown is a LaTeX-inspired markup language for creating
    interactive HTML presentations from plain text.

    .o{Text-first authoring - write presentations like you write code}
    .o{Behavioral markup - \.directive\{content\} syntax}
    .o{Interactive effects - typewriter animations, progressive reveals}
    .o{Single-file workflow - one .sd source → standalone HTML}
  }
}

.slide{
  .title{Quick Start}
  .body{
    .typewriter{> Installing slidedown...}

    # Install
    pip install -e .

    # Compile a presentation
    slidedown examples/minimal/ output/ --inputFile minimal.sd

    # View it
    cd output/
    python3 -m http.server 8000
    # Open http://localhost:8000

    That's it!
  }
}

.slide{
  .title{Directive Syntax}
  .body{
    The core syntax is simple:

    \.directive\{content\}
    \.directive\{\.modifier\{value\} content\}
    \.directive\{nested \.directives\{work\} too\}

    .bf{Structure:}
    .o{\.slide\{\} - defines a slide}
    .o{\.title\{\} - slide title (metadata)}
    .o{\.body\{\} - slide content}

    .bf{Formatting:}
    .o{\.bf\{\} - bold}
    .o{\.em\{\} - italic}
    .o{\.tt\{\} - monospace}
    .o{\.code\{\} - inline code}

    .bf{Effects:}
    .o{\.typewriter\{\} - typing animation}
    .o{\.o\{\} - progressive reveal bullets}

    .bf{Transforms:}
    .o{\.font-doom\{\} - ASCII art with Figlet}
    .o{\.cowpy-cow\{\} - ASCII speech bubbles}
  }
}

.slide{
  .title{Installation}
  .body{
    .bf{Install slidedown:}

    pip install -e .

    .bf{Requirements:}
    .o{Python 3.11+}
    .o{pip or uv}
    .o{Modern web browser}

    .bf{Platform Support:}
    .o{Linux, macOS, Windows}
    .o{Android (via Termux)}
  }
}

.slide{
  .title{Usage}
  .body{
    .bf{Basic compilation:}

    slidedown inputdir/ outputdir/ --inputFile presentation.sd

    .bf{With theme:}

    slidedown input/ output/ --inputFile demo.sd --theme retro-terminal

    .bf{Available themes:}
    .o{conventional-light (default)}
    .o{conventional-dark}
    .o{retro-terminal}
    .o{terminal}
    .o{lcars-lower-decks}
  }
}

.slide{
  .title{Example Presentation}
  .body{
    .font-standard{HELLO}

    Here's a minimal example:

    .slide{.style{background: black; color: lightgreen;}
      .title{My First Slide}
      .body{
        .typewriter{> Initializing presentation...}

        .bf{Features:}
        .o{.em{Text-first} authoring}
        .o{.tt{Behavioral} markup}
        .o{Interactive .bf{effects}}

        .cowpy-tux{Made with slidedown!}
      }
    }
  }
}

.slide{
  .title{Development Status}
  .body{
    .bf{Working:}
    .o{Parser - recursive directive parsing with placeholder substitution}
    .o{Compiler - AST to HTML with inside-out compilation}
    .o{CLI - functional command-line interface}
    .o{Tests - 65 tests passing (parser, modifiers, nesting, e2e)}
    .o{Assets - CSS/JS/HTML templates from tslide}

    .bf{In Progress:}
    .o{Browser effects debugging (typewriter, bullets, navigation)}
    .o{Documentation and examples}
    .o{Additional directives and features}
  }
}

.slide{
  .title{Project Structure}
  .body{
    slidedown/
    ├── src/
    │   ├── __main__.py          # CLI entry point
    │   ├── lib/
    │   │   ├── parser.py        # .sd syntax parser
    │   │   ├── compiler.py      # AST → HTML compiler
    │   │   └── directives.py    # Directive implementations
    │   └── models/
    │       ├── state.py         # Pipeline state management
    │       ├── directives.py    # Directive type definitions
    │       └── parser.py        # Parser return types
    ├── assets/
    │   ├── css/                 # Slideshow CSS
    │   ├── js/                  # Navigation & effects JS
    │   └── html/                # HTML templates
    ├── tests/                   # Test suite
    └── examples/                # Example presentations
  }
}

.slide{
  .title{Testing}
  .body{
    .bf{Run all tests:}
    pytest

    .bf{Run specific test files:}
    pytest tests/test_parser_basic.py -v
    pytest tests/test_e2e_compilation.py -v

    .bf{Coverage report:}
    pytest --cov=slidedown --cov-report=html

    .bf{Test categories:}
    .o{test_parser_basic.py - directive parsing, nesting}
    .o{test_parser_modifiers.py - .style{} and .class{} extraction}
    .o{test_parser_nesting.py - recursive structure validation}
    .o{test_e2e_compilation.py - full pipeline integration}
  }
}

.slide{
  .title{Architecture}
  .body{
    .bf{Functional Pipeline Pattern:}

    .sd source → Parser → AST → Compiler → HTML
                   ↓         ↓        ↓
              ProgramState → → → → → →

    .bf{Key Concepts:}
    .o{.em{State Bus} - ProgramState dataclass carries state}
    .o{.em{Inside-Out Compilation} - children compiled first}
    .o{.em{Placeholder Substitution} - \\x00CHILD_N\\x00 markers}
    .o{.em{Directive Registry} - extensible handler system}
  }
}

.slide{
  .title{Navbar Customization}
  .body{
    Customize navigation with \.meta\{navbar: ...\}

    .bf{Container styling:}
    .o{background, border, padding, box-shadow}

    .bf{Button options:}
    .o{shape: "round", "square", or custom}
    .o{size: width/height (e.g., "24px")}
    .o{color, background, border, box-shadow}
    .o{icon: FontAwesome HTML entity}
    .o{tooltip: hover text}

    .bf{Available buttons:}
    .o{slide_first, slide_previous, slide_next, slide_last}
    .o{slide_counter with format: "{current}/{total}"}
    .o{title with custom color}

    .bf{Layout zones:} left, center, right

    See examples/watermarked/light-watermarks-demo.sd for full examples
  }
}

.slide{
  .title{Contributing}
  .body{
    This project was developed with .em{test-driven development}:

    1. Write tests first
    2. Implement to pass
    3. Refactor for clarity
    4. Document behavior

    .bf{Code Style:}
    .o{RPN naming: object_verb (e.g., placeHolder_make)}
    .o{Type hints everywhere}
    .o{Docstrings with Args/Returns/Examples}
    .o{Functional over imperative}

    .bf{Current Needs:}
    .o{Browser effect debugging (see GitHub issues)}
    .o{Additional directive implementations}
    .o{Documentation and tutorials}
    .o{Example presentations}
  }
}

.slide{
  .title{Credits}
  .body{
    Built on the shoulders of giants:

    .o{.bf{tslide} - Original presentation framework by rudolphpienaar}
    .o{.bf{pyfiglet} - ASCII art generation}
    .o{.bf{cowsay} - ASCII speech bubbles}
    .o{.bf{ChRIS plugin} - CLI framework pattern}
  }
}

.slide{
  .title{License & Contact}
  .body{
    .font-slant{MIT}

    Licensed under the MIT License.
    See LICENSE file for details.

    .bf{Author:} Rudolph Pienaar
    .bf{Repository:} github.com/FNNDSC/slidedown
    .bf{Issues:} github.com/FNNDSC/slidedown/issues

    .typewriter{> Happy presenting!}
  }
}
```
