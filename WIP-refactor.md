# Slidedown Architecture Refactoring

## Current Architecture Issues

### 1. Separation of Concerns Violations

**Problem in compiler.py:290-560**
```python
def lcarsFrame_generate(self, content: str, navbar_html: str) -> str:
    """290 lines of LCARS-specific HTML embedded in Compiler"""
    cascade_html = """
        <div class="data-wrapper">
            <div class="data-column">
                <div class="dc-row-1">03</div>
                ...
            </div>
        </div>"""  # 150 lines of inline HTML

    lcars_html = f"""
    <section class="wrap-all">
        ...
    </section>
    <script>
        function updateLCARSClock() {{ ... }}  # JavaScript in Python f-string
    </script>"""

    return lcars_html
```

**Issues:**
- 290 lines of theme-specific logic in generic Compiler class
- HTML structure hard-coded as Python strings (no syntax highlighting, hard to edit)
- JavaScript code embedded with double-brace escaping (`{{` and `}}`)
- LCARS is now part of the core compiler, not a theme extension

**Problem in compiler.py:574-605**
```python
is_lcars = self.theme.name.startswith('lcars')  # Fragile detection
head_template = 'head-lcars.html' if is_lcars else 'head.html'

if is_lcars:
    body_content = f"""..."""  # LCARS-specific structure
else:
    body_content = f"""..."""  # Standard structure
```

**Issues:**
- Theme detection using string prefix matching (brittle, error-prone)
- Only supports two code paths: LCARS vs. standard
- Adding new themes with custom layouts requires modifying Compiler
- Violates Open/Closed Principle (should be open for extension, closed for modification)

### 2. Lack of Extensibility

**Current Theme class (theme.py):**
```python
class Theme:
    """Just a data container - no behavior"""
    def __init__(self, theme_name: str, themes_dir: str = "themes"):
        self.name = theme_name
        self.config = self._config_load()
        self.css_path = self.theme_dir / "theme.css"

    def config_get(self, key: str, default: Any = None) -> Any:
        """Only provides configuration access"""
        pass
```

**Issues:**
- Theme has no behavior, only data
- No hooks for themes to customize compilation
- No way for themes to inject custom HTML structure
- No extensibility mechanism

### 3. Template Management

**Issues:**
- Large HTML strings embedded in Python code
- No template engine (Jinja2, Mako, etc.)
- JavaScript code as f-strings with escaping nightmares
- Templates not reusable or composable
- Hard to maintain (no IDE support for HTML/JS in Python strings)

---

## Proposed Architecture

### Design Principles

1. **Separation of Concerns**: Theme-specific logic belongs in themes, not compiler
2. **Open/Closed Principle**: Easy to add new themes without modifying compiler
3. **Template Externalization**: HTML/JS templates in separate files
4. **Hook System**: Themes can hook into compilation pipeline
5. **Backwards Compatibility**: Existing themes continue to work

---

### 1. Theme Base Class with Hooks

**New file: `src/lib/theme_base.py`**

```python
"""
Base theme classes with hook system for compilation customization
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class ThemeHooks(ABC):
    """
    Abstract base class for theme customization hooks.

    Themes can subclass this to customize compilation behavior
    without modifying the compiler.
    """

    def __init__(self, theme_dir: Path, config: Dict[str, Any]):
        self.theme_dir = theme_dir
        self.config = config
        self.templates_dir = theme_dir / "templates"

    # ===== Head/Footer Hooks =====

    def head_template_get(self) -> str:
        """
        Return name of head template file.

        Default: 'head.html'
        LCARS override: 'head-lcars.html'
        """
        return 'head.html'

    def footer_customize(self, footer_html: str, meta: Dict[str, Any]) -> str:
        """
        Customize footer HTML before injection.

        Args:
            footer_html: Default footer HTML from compiler
            meta: Metadata from .meta{} directive

        Returns:
            Customized footer HTML (or original if no changes)
        """
        return footer_html

    # ===== Body Structure Hooks =====

    def body_wrap(self, content: str, navbar_html: str, footer_html: str,
                  slide_count: int, meta: Dict[str, Any]) -> str:
        """
        Wrap slide content in theme-specific body structure.

        Args:
            content: Compiled slide content (HTML)
            navbar_html: Navigation bar HTML
            footer_html: Footer HTML
            slide_count: Total number of slides
            meta: Metadata from .meta{} directive

        Returns:
            Complete body content wrapped in theme structure

        Default implementation: Standard slidedown layout
        LCARS override: LCARS frame structure
        """
        # Default: standard slidedown layout
        return f"""    <div class="presentation-viewport">
        <div class="metaData" id="numberOfSlides" style="display: none;">{slide_count}</div>
        <div class="metaData" id="slideIDprefix" style="display: none;">slide-</div>

        {navbar_html}

        <div class="formLayout">
            {content}
        </div>

        {footer_html}
    </div>"""

    # ===== Template Rendering Hooks =====

    def template_render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with given context.

        Args:
            template_name: Name of template file (e.g., 'frame.html')
            context: Template variables (slide_count, content, etc.)

        Returns:
            Rendered HTML

        Default: Simple string formatting
        Advanced themes: Use Jinja2, Mako, etc.
        """
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template_str = template_path.read_text(encoding='utf-8')
        return template_str.format(**context)

    # ===== Asset Hooks =====

    def assets_copy(self, output_dir: Path, assets_dir: Path) -> None:
        """
        Copy theme-specific assets to output directory.

        Args:
            output_dir: Compilation output directory
            assets_dir: Source assets directory

        Override to copy additional theme assets (fonts, images, etc.)
        """
        pass


class DefaultTheme(ThemeHooks):
    """Default theme implementation (standard slidedown)"""
    pass


class LCARSTheme(ThemeHooks):
    """LCARS theme with custom frame structure"""

    def head_template_get(self) -> str:
        """Use LCARS-specific head template (no slidedown.css)"""
        return 'head-lcars.html'

    def body_wrap(self, content: str, navbar_html: str, footer_html: str,
                  slide_count: int, meta: Dict[str, Any]) -> str:
        """Wrap content in LCARS frame structure"""

        # Get LCARS-specific config
        lcars_config = meta.get('lcars', {})
        data_cascades = lcars_config.get('data_cascades', False)

        # Render LCARS frame using external template
        context = {
            'content': content,
            'slide_count': slide_count,
            'data_cascades': data_cascades,
            'title': meta.get('title', 'SLIDEDOWN')
        }

        return self.template_render('lcars-frame.html', context)
```

---

### 2. Enhanced Theme Class

**Modified: `src/lib/theme.py`**

```python
"""
Theme loader with hook system support
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Type

from .theme_base import ThemeHooks, DefaultTheme, LCARSTheme


# Registry of theme types to hook implementations
THEME_REGISTRY: Dict[str, Type[ThemeHooks]] = {
    'default': DefaultTheme,
    'lcars-lower-decks': LCARSTheme,
    'lcars-tng': LCARSTheme,  # Future LCARS variants
    'lcars-voyager': LCARSTheme,
}


class Theme:
    """
    Enhanced theme with hook support.

    Themes can now customize compilation behavior via hooks.
    """

    def __init__(self, theme_name: str, themes_dir: str = "themes"):
        self.name = theme_name
        self.themes_dir = Path(themes_dir)
        self.theme_dir = self.themes_dir / theme_name

        # Validate and load config
        self.config = self._config_load()

        # Initialize hooks for this theme
        self.hooks = self._hooks_initialize()

    def _hooks_initialize(self) -> ThemeHooks:
        """
        Initialize theme hooks based on theme type.

        Returns:
            ThemeHooks instance for this theme
        """
        # Check registry for explicit theme type
        if self.name in THEME_REGISTRY:
            hooks_class = THEME_REGISTRY[self.name]
            return hooks_class(self.theme_dir, self.config)

        # Check config for theme type specification
        theme_type = self.config.get('theme_type', None)
        if theme_type and theme_type in THEME_REGISTRY:
            hooks_class = THEME_REGISTRY[theme_type]
            return hooks_class(self.theme_dir, self.config)

        # Default: standard theme
        return DefaultTheme(self.theme_dir, self.config)

    # ... rest of existing Theme methods ...
```

---

### 3. External HTML Templates

**New directory structure:**
```
themes/lcars-lower-decks/
├── theme.yaml
├── theme.css
└── templates/
    ├── lcars-frame.html          # Main LCARS structure
    ├── lcars-data-cascade.html   # Data cascade component
    └── lcars-scripts.js          # LCARS JavaScript
```

**Example: `themes/lcars-lower-decks/templates/lcars-frame.html`**
```html
<div class="presentation-viewport">
    <div class="metaData" id="numberOfSlides" style="display: none;">{slide_count}</div>
    <div class="metaData" id="slideIDprefix" style="display: none;">slide-</div>

    <section class="wrap-all">
        <div class="wrap">
            <div class="scroll-top">
                <a id="scroll-top" href="#" onclick="scrollToTop(); return false;">
                    <span class="hop">screen</span> top
                </a>
            </div>

            <div class="left-frame-top" id="top-frame">
                <div class="panel-1">
                    <span id="lcars-date"></span>
                    <span class="hop" id="lcars-time"></span>
                </div>
                <div class="panel-2">
                    SLIDE <span class="hop navbar-counter" data-template="{{current}} / {{total}}">
                        1 / {slide_count}
                    </span>
                </div>
            </div>

            <div class="right-frame-top">
                <div class="banner">
                    <span id="pageTitle">{title}</span>
                </div>
                <div class="data-cascade-button-group">
                    {data_cascade_html}
                    <nav>
                        <button onclick="page.advance_toPrevious()">01</button>
                        <button onclick="page.advance_toNext()">02</button>
                        <button onclick="page.advance_toFirst()">03</button>
                        <button onclick="page.advance_toLast()">04</button>
                    </nav>
                </div>
                <div class="bar-panel first-bar-panel">
                    <div class="bar-1"></div>
                    <div class="bar-2"></div>
                    <div class="bar-3"></div>
                    <div class="bar-4"></div>
                    <div class="bar-5"></div>
                </div>
            </div>
        </div>

        <div class="wrap" id="gap">
            <div class="left-frame">
                <button onclick="toggleTopFrame(event)" id="topBtn" class="panel-button">
                    <span class="hop">show</span> detail
                </button>
                <div>
                    <div class="panel-3">03<span class="hop">-111968</span></div>
                    <div class="panel-4">04<span class="hop">-41969</span></div>
                    <div class="panel-5">05<span class="hop">-1701D</span></div>
                    <div class="panel-6">06<span class="hop">-081966</span></div>
                </div>
                <div>
                    <div class="panel-7">07<span class="hop">-{slide_count:02d}</span></div>
                </div>
            </div>

            <div class="right-frame">
                <div class="bar-panel">
                    <div class="bar-6"></div>
                    <div class="bar-7"></div>
                    <div class="bar-8"></div>
                    <div class="bar-9"></div>
                    <div class="bar-10"></div>
                </div>
                <main>
                    {content}
                </main>
            </div>
        </div>
    </section>

    <script src="js/lcars-scripts.js"></script>
</div>
```

**Example: `themes/lcars-lower-decks/templates/lcars-scripts.js`**
```javascript
// LCARS real-time clock
function updateLCARSClock() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour12: false });
    const date = now.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });

    const dateEl = document.getElementById('lcars-date');
    const timeEl = document.getElementById('lcars-time');

    if (dateEl) {
        dateEl.textContent = date;
    }
    if (timeEl) {
        timeEl.textContent = time;
    }
}

// Update immediately and then every second
updateLCARSClock();
setInterval(updateLCARSClock, 1000);

// Toggle top frame visibility
let topFrameHidden = false;
function toggleTopFrame(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const topFrame = document.querySelector('.left-frame-top');
    const rightFrameTop = document.querySelector('.right-frame-top');
    const button = document.getElementById('topBtn');
    const buttonText = button.querySelector('.hop');

    topFrameHidden = !topFrameHidden;

    if (topFrameHidden) {
        topFrame.classList.add('hidden');
        rightFrameTop.classList.add('hidden');
        buttonText.textContent = 'hide';
    } else {
        topFrame.classList.remove('hidden');
        rightFrameTop.classList.remove('hidden');
        buttonText.textContent = 'show';
    }
}

// Scroll to top function
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (topFrameHidden) {
        toggleTopFrame();
    }
}
```

---

### 4. Refactored Compiler

**Modified: `src/lib/compiler.py`**

```python
class Compiler:
    """
    Compiles slidedown AST to HTML - now theme-agnostic
    """

    def __init__(self, ...):
        # ... existing initialization ...
        self.theme = Theme(theme_name)  # Theme now has hooks

    def htmlDocument_build(self, content: str) -> str:
        """
        Build complete HTML document - uses theme hooks

        NO MORE THEME-SPECIFIC LOGIC HERE!
        """
        # Load head template via theme hook
        head_template = self.theme.hooks.head_template_get()
        head_html = self.template_load(head_template)

        # Generate footer and navbar
        footer_html = self.footer_generate()
        navbar_html = self.navbar_generate()

        # Allow theme to customize footer
        footer_html = self.theme.hooks.footer_customize(footer_html, self.meta_config)

        # Generate custom CSS
        custom_css = self.customCSS_generate()

        # Theme wraps body content (LCARS frame, standard layout, etc.)
        body_content = self.theme.hooks.body_wrap(
            content=f'<div class="formLayout">{content}</div>',
            navbar_html=navbar_html,
            footer_html=footer_html,
            slide_count=self.slide_count,
            meta=self.meta_config
        )

        # Assemble document
        html = f"""<!DOCTYPE html>
<html>
{head_html}{custom_css}
<body>
{body_content}

    <script src="js/slidedown.js"></script>
</body>
</html>"""

        return html

    # REMOVE: lcarsFrame_generate() - now in LCARSTheme
```

---

### 5. Conditional Template Rendering

**For advanced themes (optional enhancement):**

Install Jinja2 for proper templating:
```bash
pip install jinja2
```

**Enhanced LCARSTheme with Jinja2:**
```python
from jinja2 import Environment, FileSystemLoader

class LCARSTheme(ThemeHooks):
    """LCARS theme with Jinja2 templating"""

    def __init__(self, theme_dir: Path, config: Dict[str, Any]):
        super().__init__(theme_dir, config)

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )

    def template_render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with Jinja2"""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)
```

**Jinja2 template with conditionals:**
```html
<!-- themes/lcars-lower-decks/templates/lcars-frame.html -->
<div class="data-cascade-button-group">
    {% if data_cascades %}
        {% include 'lcars-data-cascade.html' %}
    {% endif %}

    <nav>
        <button onclick="page.advance_toPrevious()">01</button>
        <button onclick="page.advance_toNext()">02</button>
        <button onclick="page.advance_toFirst()">03</button>
        <button onclick="page.advance_toLast()">04</button>
    </nav>
</div>
```

---

## Migration Path

### Phase 1: Extract Templates (Low Risk)
1. Create `themes/lcars-lower-decks/templates/` directory
2. Move HTML strings to `.html` files
3. Move JavaScript to `.js` files
4. Update `lcarsFrame_generate()` to load from files
5. **No behavioral changes** - just file reorganization

### Phase 2: Implement Theme Hooks (Medium Risk)
1. Create `src/lib/theme_base.py` with hook definitions
2. Implement `DefaultTheme` (existing behavior)
3. Update `Theme` class to initialize hooks
4. Refactor `Compiler.htmlDocument_build()` to use hooks
5. **Backwards compatible** - existing themes use DefaultTheme

### Phase 3: Migrate LCARS to Hooks (Medium Risk)
1. Implement `LCARSTheme` class
2. Move `lcarsFrame_generate()` logic to `LCARSTheme.body_wrap()`
3. Remove LCARS-specific code from Compiler
4. Test LCARS demo presentation
5. **LCARS still works** - just cleaner implementation

### Phase 4: Optional Enhancements (Low Priority)
1. Add Jinja2 for advanced templating
2. Create template component library
3. Document theme development guide
4. Create theme scaffolding CLI tool

---

## Benefits

### For Developers
- **Maintainability**: HTML/JS in proper files with syntax highlighting
- **Extensibility**: New themes don't require modifying Compiler
- **Testability**: Theme logic isolated and unit-testable
- **Clarity**: Clear separation between compiler and theme concerns

### For Theme Authors
- **Power**: Full control over HTML structure via hooks
- **Simplicity**: Templates in familiar HTML/JS (not Python f-strings)
- **Flexibility**: Choose simple string formatting or Jinja2
- **Documentation**: Clear hook API to override

### For Users
- **Backwards Compatible**: Existing presentations work unchanged
- **More Themes**: Easier for community to create custom themes
- **Better Performance**: Templates loaded once, not regenerated
- **Consistent**: All themes follow same pattern

---

## Open Questions

1. **Template Engine**: Start with simple string formatting or require Jinja2 from the start?
   - **Recommendation**: Start simple, add Jinja2 as optional enhancement

2. **Hook Granularity**: How many hooks do we need?
   - **Recommendation**: Start minimal (head, body_wrap), add more as needed

3. **Theme Registry**: Hard-coded dict or auto-discovery?
   - **Recommendation**: Start with registry, add auto-discovery later

4. **Breaking Changes**: Any unavoidable breaking changes?
   - **Recommendation**: None - migration path is fully backwards compatible

5. **JavaScript Injection**: Should themes inject JS via hooks or templates?
   - **Recommendation**: Templates (cleaner separation, easier to maintain)

---

## Next Steps

1. **Review this design** - discuss with project owner
2. **Decide on Phase 1 scope** - what to tackle first?
3. **Create branch** - `refactor/theme-hooks`
4. **Implement Phase 1** - extract templates (low risk, high value)
5. **Test LCARS demo** - ensure no regressions
6. **Iterate** - gather feedback, adjust design
