# README Presentation

This is the compiled presentation version of the main README.md

## Viewing

- **On GitHub Pages**: Visit the link in the main README
- **Locally**: Open `index.html` in a browser or run:
  ```bash
  python3 -m http.server 8000
  ```

## Updating

To recompile after README.md changes:

```bash
./slideshow README.md --outputdir ./docs-temp --no-serve --theme conventional-light
rm -rf docs/readme-presentation/*
cp -r docs-temp/README.md/* docs/readme-presentation/
rm -rf docs-temp
git add docs/readme-presentation
git commit -m "Update README presentation"
```

Or use the Makefile target (if added):
```bash
make readme-presentation
```
