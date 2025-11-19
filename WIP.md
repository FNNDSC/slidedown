# Work in Progress - Recent Fixes & Improvements

## Status: All Issues Resolved ✓

All typewriter rendering issues fixed and custom CSS feature added.

---

## 🚀 Quick Handoff Summary

**What's Done:**
1. ✅ Fixed typewriter `>` character display (was showing `&gt;`)
2. ✅ Fixed typewriter alignment in bullet lists (was on separate lines)
3. ✅ Added custom CSS support via `.meta{css: {...}}`
4. ✅ Created platform-aware Makefile (Android/Termux + standard systems)

**On New Computer:**
```bash
cd /path/to/slidedown
make dev                  # Install deps (auto-detects platform)
make presentation         # Compile & serve default demo
# Open http://localhost:8000
```

**Current State:**
- Server may still be running on port 8000 (kill with `pkill -f "http.server"`)
- Demo uses 24px font-size via new `.meta{css: ...}` feature
- All tests passing, code ready to commit

---

## What We've Done

### 1. Watermark Sizing (COMPLETED ✓)
- Added support for percentage-based watermark sizing
- Updated validation to support all CSS units (px, %, em, rem, vw, vh, etc.)
- Updated demo to use `7%` and `10%` for monitor-independent sizing

### 2. Documentation (COMPLETED ✓)
- Created `docs/sd-guide.adoc` - comprehensive directive reference
- Created `docs/tips-n-tricks.adoc` - best practices and gotchas
- Removed all emojis from documentation (replaced with ASCII)

### 3. Directive Escaping (COMPLETED ✓)
- Implemented backslash escaping for directives: `\.directive\{...\}`
- Parser now validates directive names against registry
- Added comprehensive test suite: `tests/test_parser_escaping.py` (22 tests, all passing)
- Escaping flow: `escapes_protect()` → placeholders → `escapes_expand()` → literal text

### 4. Demo Cleanup (COMPLETED ✓)
- Removed markdown syntax (backticks, bullets) - replaced with slidedown directives
- Split Effects slide into 3 separate slides (Typewriter, ASCII Art, Cowsay)
- Added bullet characters to all `.o{}` items
- Fixed navbar title not updating (added `.trim()` in slidedown.js:817)

### 5. Typewriter Display Context (COMPLETED ✓)
- Fixed CSS specificity issue with typewriters
- `.snippet pre[id^="typewriter-"]` → inline (for bullet alignment)
- `.container pre[id^="typewriter-"]` → block (for standalone typewriters)

### 6. Typewriter Character Escaping (COMPLETED ✓)

**The Problem:**
User writes: `.typewriter{> Welcome}` or `.typewriter{\> Welcome}`
Browser displays: `&gt; Welcome` (literal characters, not the `>` symbol)

**Solution: Data attribute approach**
- Python: Store text in `data-text` attribute instead of element content
- JavaScript: Read from `getAttribute('data-text')` instead of innerHTML
- Updated locations:
  - directives.py:312-324 - generates `<pre data-text="...">`
  - slidedown.js:367 - reads from data-text (standalone function)
  - slidedown.js:517 - reads from data-text (method inside object) **[KEY FIX]**

**Issue Found:**
There were TWO `setupTypewriter` functions:
1. Line 365: Standalone function (was fixed)
2. Line 510: Method inside object (was NOT fixed - causing "undefined")

The method at line 510 is what's actually called, so it needed the same fix.

**Final Fix:**
Changed line 517 from `var HTML = t.innerHTML;` to:
```javascript
var HTML = t.getAttribute('data-text') || t.innerHTML;
```

**Status:** ✓ Working - typewriter correctly displays `>` character

### 7. Typewriter Display Context (COMPLETED ✓)

**The Problem:**
Typewriters inside `.snippet` (bullets) were displaying on separate lines instead of inline.

**Root Cause:**
CSS specificity conflict:
- `.snippet pre[id^="typewriter-"]` → `display: inline`
- `.container pre[id^="typewriter-"]` → `display: block`

Both had same specificity, so whichever came last won (block).

**Solution:**
Increased specificity of snippet rule:
- `.container .snippet pre[id^="typewriter-"]` → `display: inline` (more specific)
- `.container > pre[id^="typewriter-"]` → `display: block` (direct child only)

**Status:** ✓ Working - typewriters in bullets align correctly

### 8. Custom CSS Support via .meta{} (COMPLETED ✓)

**Feature Added:**
Users can now add arbitrary CSS properties to `.container` via `.meta{css: {...}}`:

```slidedown
.meta{
  title: "My Presentation"
  css:
    font-size: "24px"
    line-height: "1.6"
    color: "#333"
}
```

**Implementation:**
1. Added `customCSS_generate()` method in compiler.py (lines 391-430)
   - Reads `css` field from meta_config
   - Converts property names (snake_case/camelCase → kebab-case)
   - Generates inline `<style>` tag

2. Updated `htmlDocument_build()` (line 309)
   - Calls `customCSS_generate()`
   - Injects custom CSS after head.html

**Generated Output:**
```html
<!-- Custom CSS from .meta{css: ...} -->
<style>
.container {
    font-size: 24px;
    line-height: 1.6;
}
</style>
```

**Status:** ✓ Working - custom CSS applied to presentations

## Files Modified

### Core Source
- `src/lib/directives.py` - typewriter handler with data-text attribute
- `src/lib/compiler.py` - added customCSS_generate() method, updated htmlDocument_build()
- `src/lib/parser.py` - directive validation, backslash escape protection
- `src/__main__.py` - pass escaped_sequences to compiler
- `src/models/state.py` - added escapedSequences field

### Assets
- `assets/css/slidedown.css` - typewriter display context rules (lines 946-956)
  - Fixed CSS specificity: `.container .snippet pre[id^="typewriter-"]` for inline
  - Direct child selector: `.container > pre[id^="typewriter-"]` for block
- `assets/js/slidedown.js` - data-text reading for both setupTypewriter functions
  - Line 367: standalone function updated
  - Line 517: method inside object updated (KEY FIX)

### Examples
- `examples/watermarked/light-watermarks-demo.sd` - now includes css: field in .meta{}

### Documentation
- `docs/sd-guide.adoc` - comprehensive directive guide
- `docs/tips-n-tricks.adoc` - gotchas and best practices

### Tests
- `tests/test_parser_escaping.py` - 22 tests for escaping (all passing)

### Build System
- `Makefile` - platform-aware build system (NEW)
  - Auto-detects Android/Termux vs non-Android
  - Uses `pip` on Android, `uv pip` elsewhere
  - Auto-derives OUTPUT_DIR from SOURCE path
  - Targets: venv, dev, install, test, lint, format, typecheck, compile, serve, presentation
  - Example: `make presentation SOURCE=examples/myDeck/myDeck.sd`

## Quick Start (New Computer Setup)

1. **Install dependencies:**
   ```bash
   make dev
   ```
   - Auto-detects platform (Android/Termux or standard)
   - Compiles pydantic-core from source on Android (~5 min first time)

2. **Compile and serve presentation:**
   ```bash
   make presentation SOURCE=examples/watermarked/light-watermarks-demo.sd
   ```
   - Compiles to `output/watermarked/`
   - Serves on `http://localhost:8000`

3. **View in browser:**
   - Open `http://localhost:8000`
   - Use arrow keys or navbar to navigate slides

## Using the New CSS Feature

Add custom styling to any presentation:

```slidedown
.meta{
  title: "My Presentation"
  css:
    font-size: "24px"        # Larger text
    line-height: "1.6"       # Better readability
    color: "#333"            # Custom color
}
```

All CSS properties are applied to `.container` class.

## Architecture Notes

**Backslash Escape Philosophy:**
- User writes: `.typewriter{\> text}` - explicit marker for literal character
- Python processes: converts `\>` to `>` and stores safely (in data-text attribute)
- JavaScript types: gets clean string, types character-by-character
- Similar to directive escaping we already implemented

**Data Attribute Approach:**
- Bypasses HTML parsing/entity issues completely
- `data-text` holds the raw string we want to type
- `getAttribute()` returns string as-is, no entity conversion
- Clean separation between "storage" (data-text) and "display" (innerHTML)

## Test Commands

```bash
# Compile and serve (recommended)
make presentation SOURCE=examples/watermarked/light-watermarks-demo.sd

# Or separately:
make compile SOURCE=examples/watermarked/light-watermarks-demo.sd
make serve

# Run tests
make test

# Code quality
make lint
make format
make typecheck
```

## Git Status

Current branch: `main`

**Ready to commit:**
- Typewriter escaping fixes (data-text attribute approach)
- CSS specificity fixes for inline typewriters
- Custom CSS support via `.meta{css: {...}}`
- Platform-aware Makefile with auto-detection

**Modified files:**
- src/lib/compiler.py (added customCSS_generate)
- assets/js/slidedown.js (line 517 data-text fix)
- assets/css/slidedown.css (specificity fixes)
- examples/watermarked/light-watermarks-demo.sd (added css field)
- Makefile (new platform-aware build system)
- WIP.md (this file)
