# Minimal Example

A quick start guide demonstrating the core features of slidedown in a simple, easy-to-follow presentation.

## Compile

From the repository root:

```bash
./src/slidedown examples/minimal/ output/ --inputFile minimal.sd
```

## View

```bash
cd output/
python3 -m http.server 8000
```

Open http://localhost:8000 in your browser.

## What's Demonstrated

This example covers the essential features you need to create great presentations:

### Text Formatting
- `.bf{}` - **Bold** text for emphasis
- `.em{}` - *Italic* text for style
- `.code{}` - `Inline code` for technical terms
- `.underline{}` - Underlined text for highlights
- Nesting: `.bf{Bold with .em{italic inside}}`

### Heading Directives
- `.h1{}` through `.h6{}` - Clean heading syntax instead of raw HTML
- Example: `.h2{Section Title}` instead of `<h2>Section Title</h2>`

### Interactive Effects
- `.o{}` - Progressive bullet reveal (click to show next point)
- `.typewriter{}` - Character-by-character typing animation

### Layout Features
- `.column{}` - Side-by-side content layouts
- Column styling: `.column{.style{align=left; width=50%}}`
- Automatically wrapped in flex containers

### Images
- Standard HTML `<img>` tags work seamlessly
- Paths relative to output directory

## Quick Example

```
.slide{
    .title{My First Slide}
    .body{
        .h2{Welcome!}

        .o{First point appears}
        .o{Second point on click}

        <p>Mix .bf{directives} with HTML freely!</p>
    }
}
```

## Next Steps

- See **comprehensive.sd** for all available directives and advanced features
- See **code.sd** for syntax highlighting examples
