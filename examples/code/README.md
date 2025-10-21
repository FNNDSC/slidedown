# Code Syntax Highlighting Example

Demonstrates slidedown's syntax highlighting capabilities using Pygments to highlight code in multiple programming languages.

## Compile

From the repository root:

```bash
./src/slidedown examples/code/ output/ --inputFile code.sd
```

## View

```bash
cd output/
python3 -m http.server 8000
```

Open http://localhost:8000 in your browser.

## What's Demonstrated

This presentation showcases syntax highlighting for various languages:

### Languages Highlighted

1. **Python** - Recursive Fibonacci implementation
   - Keywords, function definitions, docstrings
   - f-strings and control flow

2. **C** - Linked list data structure
   - Types, pointers, struct definitions
   - Preprocessor directives, memory allocation

3. **JavaScript** - Async/await HTTP fetching
   - Modern ES6+ features, template literals
   - Promise handling, error handling

4. **Slidedown** - Custom lexer for slidedown markup
   - Directive syntax highlighting
   - Meta-example: using slidedown to show slidedown

### Syntax Highlighting Syntax

Use the `.code{}` directive with a `.syntax{}` modifier:

```
.code{.syntax{language=python}
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
}
```

### Supported Languages

Slidedown uses Pygments, which supports 500+ languages including:
- Python, C, C++, Java, JavaScript, TypeScript
- Go, Rust, Ruby, PHP, Perl
- Shell scripts (bash, zsh)
- HTML, CSS, SQL
- And many more!

For the complete list, see the [Pygments documentation](https://pygments.org/languages/).

## Styling

The code blocks use the **Monokai** theme with inline styles, providing:
- Dark background (#272822)
- Syntax-appropriate color coding
- No external CSS dependencies

## Inline vs Block Code

- **Block code**: `.code{.syntax{language=python} ... }` - Syntax highlighted
- **Inline code**: `.code{function()}` - Simple monospace styling
