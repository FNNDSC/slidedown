# Minimal Example

This example demonstrates **all available directives** in slidedown with clear, simple usage.

## Compile

From the repository root:

```bash
./src/slidedown examples/minimal/ output/ --inputFile minimal.sd -vv
```

## View

```bash
cd output/
python3 -m http.server 8000
```

Open http://localhost:8000 in your browser.

## What's Demonstrated

### Structural Directives
- `.slide{}` - Define a slide
- `.title{}` - Slide title (metadata)
- `.body{}` - Slide content area

### Text Formatting
- `.bf{}` - **Bold** text
- `.em{}` - *Emphasized* (italic) text
- `.tt{}` - `Monospace` text
- `.code{}` - Inline code
- `.underline{}` - Underlined text

### Special Effects
- `.typewriter{}` - Character-by-character typing animation
- `.o{}` - Progressive bullet reveal (click to show next)

### ASCII Art
- `.font-<name>{}` - Figlet ASCII art fonts
  - Available: `standard`, `slant`, `banner`, `doom`, `basic`
  - Example: `.font-doom{DOOM}`

### Cowsay Characters
- `.cowpy-<char>{}` - ASCII speech bubbles
  - Available: `cow`, `tux`, `dragon`, `moose`, `random`
  - Example: `.cowpy-tux{Hello from Tux!}`

## Syntax Notes

**Nesting:** Directives can be nested within each other:
```
.o{This is .bf{bold} inside a bullet}
```

**Advanced Nesting:** Complex combinations are possible:
```
.typewriter{
Instructions:
.o{Step 1 appears after typing}
.o{Step 2 appears on click}
}
```

**Raw HTML:** Mix HTML freely with directives:
```
<h2>HTML Title</h2>
.bf{Bold directive text}
<p>HTML paragraph</p>
```

**Whitespace:** Whitespace inside `{}` is preserved in content but flexible around directives.
