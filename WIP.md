# Work in Progress - Typewriter Escaping Fix

## Current Issue
Working on fixing typewriter rendering where `>` character displays as `&gt;` in browser.

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

### 6. Typewriter Character Escaping (IN PROGRESS ⚠️)

**The Problem:**
User writes: `.typewriter{> Welcome}` or `.typewriter{\> Welcome}`
Browser displays: `&gt; Welcome` (literal characters, not the `>` symbol)

**What We've Tried:**

1. **Attempt 1**: Used `html.escape()` in Python
   - Result: Created the problem initially

2. **Attempt 2**: Removed `html.escape()` entirely
   - Result: Still showed `&gt;`

3. **Attempt 3**: Changed JavaScript from `innerHTML` to `textContent`
   - Changed `setupTypewriter()` line 366
   - Changed caching at lines 648, 651, 749, 773
   - Result: Still showed `&gt;`

4. **Attempt 4**: Added backslash escape syntax `\>` → converts to `&gt;` entity
   - Modified `typewriter_handler()` in directives.py
   - Updated demo to use `\>` in source
   - Result: Still showed `&gt;`

5. **Attempt 5 (CURRENT)**: Data attribute approach
   - Python: Store text in `data-text` attribute instead of element content
   - JavaScript: Read from `getAttribute('data-text')` instead of innerHTML/textContent
   - Updated locations:
     - directives.py:312-324 - generates `<pre data-text="...">`
     - slidedown.js:367 - reads from data-text
     - slidedown.js:649, 652-653 - caching with data-text
     - slidedown.js:751-752 - restore with data-text
     - slidedown.js:776 - store with data-text

**Current HTML Output:**
```html
<pre id="typewriter-1-1" data-text="&gt; Welcome to the light theme demo"></pre>
```

**Theory:**
By storing text in a data attribute, we bypass the HTML content parsing pipeline entirely.
JavaScript reads the raw attribute value, which gives us the literal string we need to type.

**Status:** Code compiled, needs browser testing

## Files Modified

### Core Source
- `src/lib/directives.py` - typewriter handler with backslash escapes and data-text
- `src/lib/compiler.py` - escape expansion, watermark validation
- `src/lib/parser.py` - directive validation, backslash escape protection
- `src/__main__.py` - pass escaped_sequences to compiler
- `src/models/state.py` - added escapedSequences field

### Assets
- `assets/css/slidedown.css` - typewriter display context rules (lines 946-956)
- `assets/js/slidedown.js` - data-text reading, textContent changes

### Examples
- `examples/watermarked/light-watermarks-demo.sd` - uses `\>` escape syntax
- `examples/watermarked/README.md` - updated documentation

### Documentation
- `docs/sd-guide.adoc` - comprehensive directive guide (NEW)
- `docs/tips-n-tricks.adoc` - gotchas and best practices (NEW)

### Tests
- `tests/test_parser_escaping.py` - 22 tests for escaping (NEW, all passing)

## Next Steps

1. **Test the data-attribute solution**
   - Restart server: `cd output/watermarked && python3 -m http.server 8000`
   - Hard refresh browser
   - Check if `>` displays correctly on slides 1, 6, and 7

2. **If still broken:**
   - Debug with browser console: check `element.getAttribute('data-text')`
   - Verify what string the typewriter is actually typing
   - Consider alternative: use a custom marker like `\x00GT\x00` that gets client-side replaced

3. **Update documentation**
   - Document the `\>` escape syntax in sd-guide.adoc
   - Add typewriter escaping section to tips-n-tricks.adoc

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
# Compile
./slideshow examples/watermarked/light-watermarks-demo.sd --theme conventional-light --no-serve

# Run tests
python -m pytest tests/test_parser_escaping.py -v

# Serve
cd output/watermarked && python3 -m http.server 8000
```
