# 🚀 DeepSeek-OCR on Windows — Local Setup Guide + Advanced Web UI

> A step-by-step guide to running **DeepSeek-OCR locally on Windows** with an NVIDIA GPU, complete with a Gradio Web UI for bulk image processing and PDF-to-Word extraction.

The official repository relies heavily on Linux-specific tools (`vLLM` and `Flash Attention 2`), which fail on Windows. This guide bypasses those limitations using the **Transformers** implementation, fixes common PyTorch tensor errors (`masked_scatter_`), and provides a powerful Gradio Web UI.

---

## 🛑 Why This Guide? (Windows-Specific Fixes)

Running the official repo on Windows will likely produce these errors:

| Error | Cause | Fix Applied |
|---|---|---|
| `vllm-0.8.5+cu118-...-manylinux1_x86_64.whl is not a supported wheel` | vLLM has no Windows wheel | Replaced with Transformers eager mode |
| Flash Attention build failure | No Windows support | Removed `_attn_implementation='flash_attention_2'` |
| Empty output / silent fails | Model prints to `stdout` instead of returning strings | Captured `stdout` and piped it to the UI |
| `masked_scatter_: expected self and source to have same dtypes` | RGBA/transparent PNG causes dtype mismatch in ViT | Force `image.convert("RGB")` + `torch.autocast` |

---

## 🛠️ Prerequisites

- Windows 10 / 11
- NVIDIA GPU (**10 GB+ VRAM recommended**)
- [Anaconda](https://www.anaconda.com/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) installed
- [Git](https://git-scm.com/) installed

---

## 📦 Installation

### Step 1 — Clone the Official Repository

```bash
git clone https://github.com/deepseek-ai/DeepSeek-OCR.git
cd DeepSeek-OCR
```

### Step 2 — Create and Activate Conda Environment

```bash
conda create -n deepseek-ocr python=3.12.9 -y
conda activate deepseek-ocr
```

### Step 3 — Install PyTorch (CUDA 11.8)

```bash
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
```

### Step 4 — Install Core Requirements

```bash
pip install -r requirements.txt
pip install transformers timm accelerate einops
```

### Step 5 — Install Web UI Dependencies

```bash
pip install gradio pymupdf python-docx markdown
```

---

## 🖥️ Running the Application

1. Place the `app.py` script inside your `DeepSeek-OCR` folder.
2. Make sure your conda environment is active, then run:

```bash
python app.py
```

> **Note:** The first run will download model weights (~7 GB) to your local cache.

3. Wait for the terminal to print: `Starting Web UI Server...`
4. Open your browser and navigate to: [http://127.0.0.1:7860](http://127.0.0.1:7860)

---

## ✨ Web UI Features (`app.py`)

### Tab 1 — Bulk Image Processing
- Upload 10+ images at once
- AI extracts text and generates formatted HTML pages
- Custom parsing reconstructs official document headers

### Tab 2 — PDF to Word / LaTeX
- Upload a PDF → pages are converted to images
- DeepSeek extracts complex math and formatting in Markdown mode
- Outputs a fully editable `.docx` file and a `.md` file

### VRAM Optimisations
- Uses `low_cpu_mem_usage=True` and `torch.bfloat16` to prevent RAM crashes during model loading

### Terminal Capture
- DeepSeek's `model.infer()` natively prints to `sys.stdout`
- The UI safely hooks into the console stream to capture and display output

---

## 🔧 Troubleshooting

**Model crashes my PC when loading**
> You may be running out of system RAM. Ensure `low_cpu_mem_usage=True` is set in `AutoModel.from_pretrained()`.

**Text output is completely empty**
> Make sure the image is converted to RGB before inference:
> ```python
> image = image.convert("RGB")
> ```
> Transparent PNGs (RGBA) cause silent math errors in the Vision Transformer.

**Out of Memory (OOM) during inference**
> In the Web UI, change the **Resolution Mode** from `Gundam (High-Res)` to `Base (1024)` or `Small (640)`.

---


This guide is provided as-is for community use. DeepSeek-OCR itself is subject to its own [official licence](https://github.com/deepseek-ai/DeepSeek-OCR).
