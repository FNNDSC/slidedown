# Slidedown

Slidedown is a text-first presentation compiler. You write a plain text
`.sd` file with simple `.directive{content}` markup, and slidedown compiles it
to a browser-based HTML presentation.

It is meant for people who want slide decks that behave more like source code:
diffable, scriptable, easy to version, and still capable of presentation
effects such as progressive reveals, typewriter text, code highlighting,
themes, and custom CSS.

View the original self-hosted README presentation:

https://fnndsc.github.io/slidedown/readme-presentation/

## Quick Start

Slidedown is primarily managed through its `Makefile`. That path assumes your
system has `make` available.

On Linux and macOS, `make` is usually available through the system package
manager or developer tools. On Windows, use WSL, MSYS2, Git Bash, or another
environment that provides GNU Make. The Makefile also detects Android/Termux
and uses `pip` there instead of `uv pip`.

From a fresh checkout:

```bash
make dev
```

Compile and serve an example deck:

```bash
make presentation SOURCE=examples/minimal/minimal.sd
```

The first command creates `.venv` and installs slidedown in editable mode. The
second command compiles the deck and serves it at:

```text
http://localhost:8000
```

Compile without serving:

```bash
make compile SOURCE=examples/minimal/minimal.sd
```

Serve an already compiled deck:

```bash
make serve SOURCE=examples/minimal/minimal.sd
```

Change the theme or port:

```bash
make presentation \
  SOURCE=examples/watermarked/light-watermarks-demo.sd \
  THEME=conventional-light \
  PORT=9000
```

See all Makefile targets:

```bash
make help
```

If you are on a system without `make`, the equivalent manual path is:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/slidedown examples/minimal/ output/ \
  --inputFile minimal.sd \
  --theme conventional-light
cd output/
python3 -m http.server 8000
```

## Minimal Example

```slidedown
.slide{
  .title{Hello Slidedown}
  .body{
    .typewriter{> Welcome...}

    .bf{Why use it?}
    .o{Text-first authoring}
    .o{Progressive reveal bullets}
    .o{Browser-native presentation output}
  }
}
```

## Core Syntax

Slidedown content is built from directives:

```slidedown
.directive{content}
.directive{.modifier{value} content}
.directive{nested .directives{work} too}
```

Common structural directives:

- `.slide{}` defines one slide
- `.title{}` defines the slide title
- `.body{}` defines the visible slide content

Common formatting and behavior directives:

- `.bf{}` bold text
- `.em{}` italic text
- `.tt{}` monospace text
- `.code{}` highlighted code block
- `.typewriter{}` typing animation
- `.o{}` progressive reveal bullet/snippet

## Themes

Use `--theme` to select a theme:

```bash
slidedown input/ output/ --inputFile deck.sd --theme retro-terminal
```

Included themes:

- `conventional-light`
- `default`
- `terminal`
- `retro-terminal`
- `lcars-lower-decks`

## Deck Metadata

Use `.meta{}` for deck-wide settings:

```slidedown
.meta{
  title: "Demo Deck"
  typography:
    baseline: presentation
  snippets:
    marker: "-> "
}
```

Typography baselines include `compact`, `normal`, `large`, `xlarge`, and
`presentation`. For per-slide tuning, add a density class:

```slidedown
.slide{.class{dense}
  .title{Detailed Slide}
  .body{
    Dense slides fit more content while preserving presentation scale.
  }
}
```

Supported density classes are `hero`, `roomy`, `dense`, and `compact`.

## Documentation

- Complete guide: [`docs/sd-guide.adoc`](docs/sd-guide.adoc)
- Tips and patterns: [`docs/tips-n-tricks.adoc`](docs/tips-n-tricks.adoc)
- LCARS theme guide: [`docs/lcars.adoc`](docs/lcars.adoc)
- Examples: [`examples/`](examples/)
- README presentation source:
  [`docs/readme-presentation.sd`](docs/readme-presentation.sd)

## Development

Run the checks:

```bash
make lint
make typecheck
make test
```

Useful development targets:

```bash
make format
make clean
make purge
make readme-presentation
```

Project conventions:

- Python code uses explicit type hints
- Python lines stay under 80 columns
- Public docstrings use Google-style `Args` and `Returns` sections
- Internal names prefer RPN-style `object_verb` naming where practical

## License

Slidedown is released under the MIT License. See [`LICENSE`](LICENSE).
