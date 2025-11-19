# Slidedown Development Makefile
#
# Automatically detects Android/Termux and uses appropriate package manager:
#   - Android/Termux: uses pip (to avoid "failed to lock" issues)
#   - Non-Android: uses uv pip (faster, more reliable)
#
# Quick start:
#   make venv      - Create virtual environment
#   make dev       - Install in editable mode with dev dependencies
#   make install   - Install package
#   make test      - Run tests
#   make lint      - Run linters
#   make clean     - Remove build artifacts

VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin

# Configurable presentation options (can be overridden)
SOURCE ?= examples/watermarked/light-watermarks-demo.sd
THEME ?= conventional-light
PORT ?= 8000

# Parse SOURCE into components for slidedown CLI
# SOURCE: examples/watermarked/light-watermarks-demo.sd
# INPUT_DIR: examples/watermarked
# INPUT_FILE: light-watermarks-demo.sd
# OUTPUT_DIR: output/watermarked
INPUT_DIR := $(dir $(SOURCE))
INPUT_FILE := $(notdir $(SOURCE))
OUTPUT_BASE := output
OUTPUT_SUBDIR := $(patsubst examples/%,%,$(INPUT_DIR))
OUTPUT_DIR := $(OUTPUT_BASE)/$(OUTPUT_SUBDIR)

# Detect Android/Termux environment
IS_ANDROID := $(shell test -d /data/data/com.termux || test -n "$$ANDROID_ROOT" && echo 1 || echo 0)

# Set package installer based on platform
ifeq ($(IS_ANDROID),1)
    PIP := $(VENV_BIN)/pip
    PLATFORM_MSG := "Android/Termux detected - using pip"
else
    PIP := uv pip
    PLATFORM_MSG := "Non-Android detected - using uv pip"
endif

.PHONY: help venv dev install test lint format typecheck clean purge shell compile serve presentation

help:
	@echo "Slidedown development targets:"
	@echo ""
	@echo "Setup:"
	@echo "  make venv       - Create virtual environment"
	@echo "  make dev        - Install in editable mode with dev dependencies"
	@echo "  make install    - Install package (production)"
	@echo ""
	@echo "Development:"
	@echo "  make presentation  - Compile and serve presentation (see variables below)"
	@echo "  make compile       - Compile presentation only"
	@echo "  make serve         - Serve compiled presentation only"
	@echo "  make shell         - Start shell with activated virtual environment"
	@echo ""
	@echo "Variables (override with: make compile SOURCE=myfile.sd THEME=dark):"
	@echo "  SOURCE=$(SOURCE)"
	@echo "  THEME=$(THEME)"
	@echo "  OUTPUT_DIR=$(OUTPUT_DIR) (auto-derived from SOURCE)"
	@echo "  PORT=$(PORT)"
	@echo ""
	@echo "Auto-Derivation:"
	@echo "  OUTPUT_DIR is automatically derived from SOURCE path:"
	@echo "    examples/watermarked/demo.sd  -> output/watermarked/"
	@echo "    examples/something/talk.sd    -> output/something/"
	@echo "  You only need to specify SOURCE, OUTPUT_DIR adapts automatically!"
	@echo ""
	@echo "Testing & QA:"
	@echo "  make test       - Run pytest"
	@echo "  make lint       - Run ruff linter"
	@echo "  make format     - Run black formatter"
	@echo "  make typecheck  - Run mypy type checker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove build artifacts"
	@echo "  make purge      - Remove build artifacts AND virtual environment"
	@echo ""
	@echo "Example Workflow:"
	@echo "  Let's say you have a new slidedown called 'myDeck.sd' and it is"
	@echo "  located in examples/myDeck/myDeck.sd -- in order to set everything"
	@echo "  up and serve the presentation you do:"
	@echo ""
	@echo "  1. Setup from scratch (first time only):"
	@echo "       make dev"
	@echo ""
	@echo "  2. Compile and serve your presentation:"
	@echo "       make presentation SOURCE=examples/myDeck/myDeck.sd"
	@echo ""
	@echo "  This will automatically:"
	@echo "    - Use the virtual environment (no need to activate manually)"
	@echo "    - Compile examples/myDeck/myDeck.sd with theme $(THEME)"
	@echo "    - Output to output/myDeck/ (auto-derived)"
	@echo "    - Serve on http://localhost:$(PORT)"
	@echo ""
	@echo "  Note: 'make' targets automatically use the venv, no activation needed!"
	@echo ""
	@echo "Platform: $(PLATFORM_MSG)"

venv:
	test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@echo "Virtual environment created. Activate with: source $(VENV_BIN)/activate"
	@echo "Platform: $(PLATFORM_MSG)"

dev: venv
	@echo "Installing slidedown in editable mode..."
	@echo "Platform: $(PLATFORM_MSG)"
ifeq ($(IS_ANDROID),1)
	@echo "Android/Termux detected - installing without dev dependencies (no ruff/black/mypy)"
	@echo "This may take several minutes as some packages compile from source..."
	$(PIP) install -e .
	@echo ""
	@echo "SUCCESS: Slidedown core installed (skipped dev tools: ruff, black, mypy, pytest)"
	@echo "These tools require additional Rust compilation and are not needed for basic usage"
else
	$(PIP) install -e ".[dev]"
	@echo "Installed slidedown in editable mode with dev dependencies"
endif

install: venv
	@echo "Installing slidedown..."
	@echo "Platform: $(PLATFORM_MSG)"
	$(PIP) install .
	@echo "Installed slidedown"

test:
	$(VENV_BIN)/pytest -v

lint:
	$(VENV_BIN)/ruff check .

format:
	$(VENV_BIN)/black .

typecheck:
	$(VENV_BIN)/mypy src

compile:
	@echo "Compiling $(SOURCE) with theme $(THEME)..."
	@echo "  Input dir:  $(INPUT_DIR)"
	@echo "  Input file: $(INPUT_FILE)"
	@echo "  Output dir: $(OUTPUT_DIR)"
	$(VENV_BIN)/slidedown $(INPUT_DIR) $(OUTPUT_BASE) \
		--inputFile $(INPUT_FILE) \
		--outputSubdir $(OUTPUT_SUBDIR) \
		--theme $(THEME)
	@echo "Compiled to $(OUTPUT_DIR)/"

serve:
	@echo "Serving presentation on http://localhost:$(PORT)"
	@echo "Press Ctrl+C to stop"
	cd $(OUTPUT_DIR) && python3 -m http.server $(PORT)

presentation: compile serve

clean:
	rm -rf build/ dist/ *.egg-info .mypy_cache .pytest_cache
	rm -rf output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned build artifacts"

purge: clean
	rm -rf $(VENV_DIR)
	@echo "Removed virtual environment"

shell: venv
	@echo "Starting shell with activated venv (exit to return)..."
	@bash -c "source $(VENV_BIN)/activate && exec bash"
