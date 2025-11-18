# Watermarked Slidedown Demo

Light-theme sample deck that demonstrates slidedown behaviors with dual watermarks.

## Files
- `light-watermarks-demo.sd` – the presentation source; watermarks set via `.meta{}` to `logos/slidedown-light.svg` (bottom-right) and `logos/ChRONOS.png` (top-left).
- `logos/` – local copies of the watermark images (paths resolve relative to the slide directory and match the output layout).

## Build and serve (recommended)
```bash
./slideshow examples/watermarked/light-watermarks-demo.sd --theme conventional-light
```
- Output goes to `output/watermarked/` (name derived from the parent folder)
- Auto-starts `python3 -m http.server 8000` unless you pass `--no-serve`
- Use `--port 9000` (or another port) to change the server port

## Manual build (alternate)
```bash
slidedown examples/watermarked/ output/watermarked/ --inputFile light-watermarks-demo.sd --theme conventional-light
cd output/watermarked/ && python3 -m http.server 8000
```
