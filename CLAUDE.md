# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask-based web UI for local AI image generation using Ollama. The application provides a clean, responsive interface for generating images from text prompts, with a gallery view for browsing historical generations.

## Development Commands

### Running the Application
```bash
# Install dependencies (uses uv for Python package management)
uv sync

# Run the development server (runs on port 8090)
uv run python app.py
```

### Utilities
```bash
# Rebuild history.json from existing images in data/images/
uv run python rebuild_history.py
```

## Environment Setup

1. **Ollama must be installed and running** before starting the app
   ```bash
   # Install Ollama (macOS/Linux)
   curl -fsSL https://ollama.com/install.sh | sh

   # Start Ollama service
   ollama serve
   ```

2. **Pull an image generation model** (models with `x/` prefix)
   ```bash
   ollama pull x/flux2-klein:9b
   ollama pull x/z-image-turbo:fp8
   ```

3. **Configure Ollama host** (optional, defaults to `http://127.0.0.1:11434`)
   ```bash
   export OLLAMA_HOST=http://192.168.1.100:11434
   ```

## Architecture

### Core Application (`app.py`)
- Single-file Flask application with all routes and logic
- **Image generation flow**: POST /api/generate → Ollama API → decode base64 → save to data/images/ → update history.json
- **Static file route**: `/static/images/<filename>` serves generated images from data/images/

### Frontend Structure
- **Templates**: Jinja2 templates extending `base.html`
  - `base.html`: Contains navigation, theme toggle, Tailwind CDN config, and CSS custom properties for theming
  - `index.html`: Image generation form with live result preview
  - `gallery.html`: Responsive grid gallery with model filtering and delete functionality
- **Styling**: Tailwind CSS via CDN with custom CSS variables for light/dark theme support
- **Theme**: Client-side theme persistence via localStorage, flash-prevention script applies theme before render

### Data Persistence
- **Images**: `data/images/<timestamp>.png` - timestamp format: `YYYY-MM-DD-HH-MM-SS`
- **History**: `data/history.json` - JSON array limited to 100 entries, newest first
- Each history entry contains: timestamp, model, width, height, prompt, image_path, duration

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Image generation page |
| `/gallery` | GET | Gallery view |
| `/api/generate` | POST | Generate image (prompt, model, width, height) |
| `/api/history` | GET | Get all history entries |
| `/api/delete/<timestamp>` | DELETE | Delete image and history entry |
| `/static/images/<filename>` | GET | Serve generated images |

### Key Constraints
- **Image dimensions**: 256-2048 pixels, must be multiples of 64
- **Timeout**: 300 seconds for Ollama API calls
- **History limit**: 100 entries (oldest trimmed when exceeded)

## Development Notes

- The app runs on port **8090** (not the default Flask 5000)
- Tailwind CSS is loaded via CDN - no build step required for styling
- The `style.css` file exists but is mostly superseded by Tailwind utility classes
- Chinese language UI (labels and messages are in Chinese)
- Theme system uses CSS custom properties defined in `base.html` `<style>` block
