# mflux WebUI

**English** | [中文](README.zh-CN.md)

A local image generation WebUI for Apple Silicon Macs: Flask backend, Alpine.js and daisyUI 5 frontend, inference powered by [mflux](https://github.com/mflux-community/mflux) and MLX. Weights and prompts never leave your machine.

Text-to-image, reference-image editing, Qwen multi-reference editing, model cache management, an async queue, task logs and a gallery. A [macOS desktop build](docs/desktop.md) (Tauri 2) opens like a native app without installing Python or Node.js, and downloads models on first use. Installers are on [GitHub Releases](https://github.com/wyf0931/mflux-webui/releases).

## Features

- **Models**: Qwen Image 2.1 Turbo, Krea 2 Turbo, Z-Image Turbo, FLUX.2 Klein, in q4 / q8 / 4-bit quantizations.
- **Reference images**: pick a file or paste with ⌘V / Ctrl+V, preview, replace or remove; uploaded only when you generate.
- **Qwen multi-reference editing**: switch generation mode, add 1–10 images in order, and refer to them as "image one"/"figure 2" or `<image1>` / `<image2>`. The original single-image composition mode still works.
- **Image-to-Text page (图生文)**: a standalone page where a local Qwen3-VL model turns any image into a one-line prompt plus seven structured dimensions, with copy and one-click handoff to the generate page.
- **Per-model defaults**: steps and guidance follow the selected model; Qwen Turbo runs 8 steps with guidance fixed at 1.0.
- **Queue**: status, model alias, elapsed time and results, with a log dialog showing full failure stacks.
- **UI**: daisyUI Rausch light theme with a dark variant, Chinese font fallbacks, mobile layout.
- **Channels**: Hugging Face and ModelScope, using each SDK's default model cache.

## Screenshots

| Generate | Gallery | Models |
| --- | --- | --- |
| ![Generate page](docs/images/generate.png) | ![Gallery page](docs/images/gallery.png) | ![Models page](docs/images/models.png) |

| Queue | Task log dialog |
| --- | --- |
| ![Queue page](docs/images/queue.png) | ![Task log dialog](docs/images/task-logs.png) |

Screenshots use sample tasks and contain no user history.

## Requirements

Apple Silicon Mac (M1 or later) with MLX support. Intel Macs, Windows and Linux are not supported. Development also needs Python 3.11+, Node.js 20+ with npm, and [uv](https://docs.astral.sh/uv/); the desktop build needs none of them.

Unified memory is the real constraint: MLX holds the full weights plus activations during sampling, and the peak is roughly twice the on-disk size of the model at 1024×1024. Close other memory-hungry apps before generating, and remember macOS itself needs a few GB.

### Recommended configurations

| Tier | Hardware | Free disk | What runs comfortably |
| --- | --- | --- | --- |
| Minimum | M1/M2, 16 GB unified memory | 30 GB | FLUX.2 Klein 4B · 4-bit at 1024×1024 (peak ≈ 10 GB); Z-Image Turbo 4-bit at 768×768 |
| Recommended | M2 Pro / M3 / M4, 32 GB | 60 GB | Qwen Image 2.1 Turbo · q4 at 1024×1024 (peak ≈ 20 GB), FLUX.2 Klein 9B · q4 at 1024×1024 |
| Comfortable | M4 Pro or better, 48 GB | 120 GB | Krea 2 Turbo · q4 at 1024×1024 (peak ≈ 31 GB), reference prompt analysis in the same session |
| Heavy | M4 Max or better, 64 GB | 200 GB | Krea 2 Turbo · q8 at 1024×1024 or larger (peak ≈ 42 GB), multi-reference editing on large canvases |

Disk budget: the recommended model set is 4.3–20.7 GB per model (about 64 GB for all six), the optional Qwen3-VL 8B 4-bit weights are 5.8 GB, and the Python environment adds roughly 3 GB.

### Measured performance

Measured on a MacBook Pro (Apple M4 Pro, 14-core, 48 GB unified memory), macOS 26.5.2, 1024×1024, 8 steps, Turbo schedule:

| Model | Weights | Peak MLX memory | Wall time |
| --- | --- | --- | --- |
| Qwen Image 2.1 Turbo · q4 | 10.0 GB | 20.5 GB | 93 s |
| Krea 2 Turbo · q4 | 14.7 GB | 31.3 GB | 185 s |
| Qwen Image 2.1 Turbo · q4 at 512×512 | 10.0 GB | 14.3 GB | 22 s |

The idle Flask backend uses about 60 MB RSS before any model is loaded. Peaks for models not listed above scale at about 2.1× their weight size at 1024×1024, and halve again at 512×512.

## Quick start

```bash
git clone https://github.com/wyf0931/mflux-webui.git
cd mflux-webui
uv sync
npm install
npm run build
uv run python app.py
```

Open <http://127.0.0.1:8090>, download a model from the Models page, then generate. `uv sync` pins mflux to the commit that adds Qwen Image 2.1 Turbo support, so do not install a global mflux on the side.

For background operation use `./ops.sh start|stop|status|logs`, and build the desktop app with `./ops.sh build`; see [Development and operations](docs/development.md).

## Dependencies and licenses

Direct Python dependencies, plus the notable transitive packages that ship in the environment:

| Dependency | Version | License | Role |
| --- | --- | --- | --- |
| [mflux](https://github.com/mflux-community/mflux) | 0.22.0 (`602b26d`) | MIT | Model loading, schedulers, inference |
| [MLX](https://github.com/ml-explore/mlx) | 0.32.3 | MIT | Apple Silicon array framework |
| [MLX-LM](https://github.com/ml-explore/mlx-lm) | 0.32.2 | MIT | Language-model utilities |
| [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) | 0.6.3 | MIT | Local Qwen3-VL reference prompt analysis |
| [Flask](https://github.com/pallets/flask) | 3.1.2 | BSD-3-Clause | HTTP server and pages |
| [huggingface_hub](https://github.com/huggingface/huggingface_hub) | 1.8.0 | Apache-2.0 | Hugging Face cache and downloads |
| [ModelScope](https://github.com/modelscope/modelscope) | 1.39.1 | Apache-2.0 | ModelScope cache and downloads |
| [Transformers](https://github.com/huggingface/transformers) | 5.15.1 | Apache-2.0 | Tokenizers, processors, VLM configs |
| [PyTorch](https://github.com/pytorch/pytorch) | 2.14.1 | BSD-3-Clause (composite) | Pulled in by the model stack |
| [OpenCV Python](https://github.com/opencv/opencv-python) | 4.13.0.92 | Apache-2.0 | Image ops required by mlx-vlm |
| [safetensors](https://github.com/huggingface/safetensors) | 0.8.0 | Apache-2.0 | Weight file format |
| [tokenizers](https://github.com/huggingface/tokenizers) | 0.22.2 | Apache-2.0 | Text tokenization |
| [NumPy](https://github.com/numpy/numpy) | 2.4.4 | BSD-3-Clause | Array math |
| [SciPy](https://github.com/scipy/scipy) | 1.17.1 | BSD-3-Clause | Audio/resampling helpers in MLX stack |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.3.0 | MIT-CMU | Image encoding and decoding |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.3 | BSD-3-Clause | `.env` loading |
| [TinyDB](https://github.com/msiemens/tinydb) | 4.8.2 | MIT | History and queue records |
| [socksio](https://github.com/sethmlarson/socksio) | 1.0.0 | MIT | SOCKS proxy support for HTTP clients |

Frontend and desktop toolchain:

| Dependency | Version | License | Role |
| --- | --- | --- | --- |
| [Alpine.js](https://github.com/alpinejs/alpine) | 3.16.2 | MIT | Page interactivity |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) | 4.3.3 | MIT | Layout utilities |
| [daisyUI](https://github.com/saadeghi/daisyui) | 5.7.17 | MIT | Component library and themes |
| [esbuild](https://github.com/evanw/esbuild) | 0.28.2 | MIT | JavaScript bundling |
| [Tauri](https://github.com/tauri-apps/tauri) | 2.x | MIT OR Apache-2.0 | Desktop shell (Rust) |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.22.3 | GPL-2.0-or-later with bootloader exception | Desktop backend packaging, build time only |

Notes:

- No inpainting model such as LaMa is used or downloaded; generation goes through the mflux model families listed above.
- Model weights are not bundled. Each checkpoint carries its own license on Hugging Face or ModelScope; review the model card before use, especially for commercial use.
- The project itself is released under the [ISC License](LICENSE).

## Documentation

| Document | Contents |
| --- | --- |
| [Docs index](docs/README.md) | Navigation for all documents (Chinese) |
| [Usage guide](docs/usage.md) | Text-to-image, image-to-image, Qwen multi-reference editing, queue and logs |
| [Models and configuration](docs/configuration.md) | Model catalog, download channels, environment variables, data locations |
| [Image-to-Text (图生文)](docs/image-description.md) | Standalone image-to-text page, local Qwen3-VL setup, output structure and API |
| [macOS desktop app](docs/desktop.md) | Install, separate data directory, local build, GitHub Actions and releases |
| [Development and operations](docs/development.md) | Install, build, background runs, automated checks, project layout |
| [Theme and components](docs/theme.md) | daisyUI theme tokens, system fonts, component conventions |
| [Qwen Image 2.1 Turbo notes](docs/qwen-image-21-turbo.md) | Pinned dependency, model requirements, troubleshooting |
| [Contributing guide](AGENTS.md) | Development commands and collaboration rules (Chinese) |

## Development checks

```bash
npm run build
node --test tests/js/*.test.cjs
uv run python -m unittest discover -s tests
uv lock --check
uv run python -m compileall app.py mflux_webui tests
uv run --with ruff ruff check app.py mflux_webui tests
```

Issues and pull requests are welcome. Describe user-visible behaviour changes, include reproduction steps for bugs, and run the checks above before opening a PR.

## License

Released under the [ISC License](LICENSE).
