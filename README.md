# mflux WebUI

[中文文档](README.zh-CN.md)

A local Flask web UI for running mflux image models with text-to-image, image-to-image, model cache management, and a generation gallery.

## Highlights

- Supports Krea 2 Turbo, Z-Image Turbo, and FLUX.2 Klein model families.
- Uses Alpine.js and DaisyUI for a lightweight responsive interface.
- Lists installed models separately from curated recommendations.
- Downloads from Hugging Face and ModelScope using each SDK's default cache directory.
- Supports dark mode, mobile layouts, reference-image editing, and gallery history.

## Screenshots

| Generate | Gallery | Models |
| --- | --- | --- |
| ![Generate page](docs/images/generate.png) | ![Gallery page](docs/images/gallery.png) | ![Models page](docs/images/models.png) |

## Requirements

- macOS on Apple Silicon
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm

The first generation or model download may fetch several gigabytes of weights. Make sure your machine has enough disk space and memory for the selected model.

## Installation

```bash
git clone https://github.com/wyf0931/mflux-webui.git
cd mflux-webui
uv sync
npm install
npm run build
```

## Run

```bash
uv run python app.py
```

Open <http://127.0.0.1:8090> in your browser.

For background operation:

```bash
./ops.sh start
./ops.sh status
./ops.sh status --watch
./ops.sh logs
./ops.sh restart
./ops.sh stop
```

Logs are written to `logs/app.log`; the process ID is written to `logs/app.pid`.
`status --watch` refreshes process CPU, memory, and platform GPU utilization every five seconds. `logs` follows the latest application log without writing monitor output to the log file.

## Model repositories

Curated models are defined in [`config/models.json`](config/models.json), loaded when the application starts. Each entry can provide a Hugging Face ID, a ModelScope ID, or both.

The `MODEL_REPO` setting controls which recommendation and download channels are enabled:

| Value | Enabled channels |
| --- | --- |
| `all` | Hugging Face and ModelScope (default) |
| `huggingface` | Hugging Face only |
| `modelscope` | ModelScope only |

Copy `.env.example` to `.env` and change the value if needed:

```bash
cp .env.example .env
```

Downloads use the default cache locations managed by `huggingface_hub` and `modelscope`; the application does not move or replace those files.

## Usage

### Text-to-image

Choose an installed model, enter a prompt, select an aspect ratio, and generate an image. Advanced controls include inference steps, guidance, and seed.

### Image-to-image

Upload a PNG, JPG, JPEG, or WebP reference image and choose an image strength from `0` to `1`. Uploaded references are temporary and removed after generation.

### Model library

The model page shows installed models first. The recommendation section provides Hugging Face and ModelScope tabs, repository links, download progress, and cancellation for active downloads.

### Generation feedback

mflux returns a complete image after inference. It does not expose an intermediate image stream through the current Python API, so the generation page shows an elapsed-time indicator while the request is running and displays the image when inference completes.

## Data locations

| Data | Location |
| --- | --- |
| Generated images | `data/images/` |
| Generation history | `data/db.json` |
| Temporary reference images | `data/uploads/` |
| Application logs | `logs/app.log` |
| Model weights | SDK-managed default caches |

## Development

```bash
uv run python -m unittest discover -s tests
uv lock --check
uv run --with ruff ruff check app.py mflux_webui tests
npm run build
uv run python -m compileall app.py mflux_webui tests
```

The application uses Flask for the page shell and API, Alpine.js for local page state, Tailwind CSS + DaisyUI for styling, and mflux for local inference.

## Project structure

```text
mflux_webui/       Flask application package, routes, services, and assets
config/            Curated model configuration
tests/             Unit tests and mocked inference coverage
data/              Runtime image and history data
docs/              Design notes and screenshots
app.py             Backward-compatible development entry point
```

## Contributing

Issues and pull requests are welcome. Please describe the user-facing behavior, include reproduction steps for bugs, and run the development checks before submitting a pull request.

## License

This project is distributed under the [ISC License](LICENSE).
