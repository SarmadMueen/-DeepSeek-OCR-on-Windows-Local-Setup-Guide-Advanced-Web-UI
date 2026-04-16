import gradio as gr
import torch
from transformers import AutoModel, AutoTokenizer
import os
import sys
from PIL import Image
import glob
from datetime import datetime
import io
import contextlib
import re

# Try importing extra libraries for the features
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import fitz  # PyMuPDF for handling PDFs
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# Import python-docx for Word document generation and styling
try:
    from docx import Document
    from docx.shared import RGBColor, Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Import pypandoc for high-quality Word generation (Tables + Native Equations)
try:
    import pypandoc
    HAS_PYPANDOC = True
    # Automatically download the Pandoc binary if it's not installed on Windows
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        print("Pandoc binary not found. Downloading automatically for high-quality Word conversion...")
        pypandoc.download_pandoc()
except ImportError:
    HAS_PYPANDOC = False

# Configuration
model_name = 'deepseek-ai/DeepSeek-OCR'
os.environ["CUDA_VISIBLE_DEVICES"] = '0'

# Create directories for outputs
OUTPUT_DIR = r"C:\Users\sarma\DeepSeek-OCR\ocr_outputs"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Step 1: Initializing Tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
except Exception as e:
    print(f"Error loading tokenizer: {e}")
    sys.exit(1)

print("Step 2: Loading Model (Memory Optimized Mode)...")
try:
    model = AutoModel.from_pretrained(
        model_name, 
        trust_remote_code=True, 
        use_safetensors=True,
        torch_dtype=torch.bfloat16, 
        low_cpu_mem_usage=True
    )
    print("Step 3: Moving model to GPU...")
    model = model.eval().cuda()
    print("Step 4: Model successfully loaded to GPU!")
except Exception as e:
    print(f"\nCRITICAL ERROR LOADING MODEL: {e}")
    sys.exit(1)

def run_deepseek_inference(image, task_type, model_size):
    """Helper function to run the model on a single PIL Image"""
    prompts = {
        "Markdown Conversion": "<image>\n<|grounding|>Convert the document to markdown. ",
        "Free OCR": "<image>\nFree OCR. ",
        "Extract Text": "<image>\nExtract all text from the image. ",
        "Figure Parsing": "<image>\nParse the figure. "
    }
    size_configs = {
        "Tiny (512)": {"base_size": 512, "image_size": 512, "crop_mode": False},
        "Small (640)": {"base_size": 640, "image_size": 640, "crop_mode": False},
        "Base (1024)": {"base_size": 1024, "image_size": 1024, "crop_mode": False},
        "Gundam (High-Res)": {"base_size": 1024, "image_size": 640, "crop_mode": True}
    }
    config = size_configs[model_size]
    prompt = prompts[task_type]
    
    temp_path = os.path.join(os.getcwd(), "temp_inference.jpg")
    image.save(temp_path)

    f = io.StringIO()
    with torch.no_grad():
        with torch.autocast(device_type="cuda", dtype=model.dtype):
            with contextlib.redirect_stdout(f):
                model.infer(
                    tokenizer,
                    prompt=prompt,
                    image_file=temp_path,
                    output_path=OUTPUT_DIR,
                    base_size=config["base_size"],
                    image_size=config["image_size"],
                    crop_mode=config["crop_mode"],
                    save_results=True,
                    test_compress=True
                )
    
    console_output = f.getvalue()
    cleaned_text = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', console_output)
    cleaned_text = re.sub(r'<\|det\|>.*?<\|/det\|>', '', cleaned_text)
    
    final_lines = []
    for line in cleaned_text.split('\n'):
        line_stripped = line.strip()
        if not line_stripped or (all(c == '=' for c in line_stripped) and len(line_stripped) > 5) or \
           line_stripped.startswith("BASE:") or line_stripped.startswith("PATCHES:") or "torch.Size" in line_stripped or \
           line_stripped.startswith("The attention layers in this model"):
            continue
        if line_stripped.startswith("image size:") or line_stripped.startswith("valid image tokens:"):
            break 
        final_lines.append(line)
        
    if os.path.exists(temp_path): os.remove(temp_path)
    return '\n'.join(final_lines).strip()

# ==========================================
# TOOL 2: PDF TO HIGH-QUALITY WORD (WITH NATIVE MATH & TABLES)
# ==========================================
def create_cv_word_template():
    """Generates a .docx template with specific CV styles (Blue Headings, Serif Font, Bottom Border)"""
    if not HAS_DOCX:
        return "Error: python-docx library is not installed.", None
        
    doc = Document()
    
    def add_bottom_border(style_element, color_hex="1E50A0"):
        """Helper to inject XML for a bottom border in a Word style."""
        pPr = style_element.get_or_add_pPr()
        pbdr = pPr.find(qn('w:pBdr'))
        if pbdr is None:
            pbdr = OxmlElement('w:pBdr')
            pPr.append(pbdr)
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')  # Thickness
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), color_hex)
        pbdr.append(bottom)

    # Modify Normal Style (Base text)
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(11)

    # Modify Heading 1
    style_h1 = doc.styles['Heading 1']
    style_h1.font.name = 'Times New Roman'
    style_h1.font.size = Pt(16)
    style_h1.font.color.rgb = RGBColor(30, 80, 160) # CV Dark Blue
    add_bottom_border(style_h1.element, "1E50A0")

    # Modify Heading 2
    style_h2 = doc.styles['Heading 2']
    style_h2.font.name = 'Times New Roman'
    style_h2.font.size = Pt(14)
    style_h2.font.color.rgb = RGBColor(30, 80, 160) # CV Dark Blue
    add_bottom_border(style_h2.element, "1E50A0")
    
    # Save the template
    template_path = os.path.join(OUTPUT_DIR, "cv_style_template.docx")
    doc.save(template_path)
    
    return "✅ CV Template created successfully. You can download it below and use it as a Reference Document.", [template_path]

def clean_markdown_formatting(text):
    """
    DeepSeek often outputs markdown syntax (##, -, *) attached to the previous line.
    Pandoc requires blank lines before headings and lists to render them properly in Word.
    This function forces proper spacing so Word renders native structural formats.
    """
    if not text: return text
    
    # 1. Add blank line before headings if missing
    text = re.sub(r'([^\n])\n(#{1,6}\s)', r'\1\n\n\2', text)
    # 2. Add blank line after headings if missing
    text = re.sub(r'(#{1,6}\s.*)\n([^\n])', r'\1\n\n\2', text)
    # 3. Add blank line before lists/bullets if the previous line isn't a bullet
    text = re.sub(r'([^\n\-\*\s])\n(\s*[-*]\s)', r'\1\n\n\2', text)
    # 4. Add blank line before markdown tables
    text = re.sub(r'([^\n\|\s])\n(\|.*\|)\n(\|[-:\s]+\|)', r'\1\n\n\2\n\3', text)
    
    return text

def process_pdf_to_word(pdf_file, reference_doc, model_size):
    if not HAS_FITZ or not HAS_PYPANDOC:
        return "Error: Required libraries missing. Please run `pip install pymupdf pypandoc` in your terminal.", None

    if pdf_file is None:
        return "Please upload a PDF file.", None

    pdf_path = pdf_file.name
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_files = []
    full_extracted_text = ""
    
    try:
        # Open PDF
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        
        for page_num in range(total_pages):
            print(f"Processing Page {page_num + 1}/{total_pages}...")
            page = pdf_document.load_page(page_num)
            
            # Convert PDF page to high-res Image 
            zoom_matrix = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Run DeepSeek OCR
            page_text = run_deepseek_inference(img, "Markdown Conversion", model_size)
            
            # APPLY THE SPACING FIXER HERE
            page_text = clean_markdown_formatting(page_text)
            
            full_extracted_text += f"\n\n# --- Page {page_num + 1} ---\n\n"
            full_extracted_text += page_text

        # ---------------------------------------------------------
        #  CONVERT TO HIGH-QUALITY WORD DOCX USING PANDOC
        # ---------------------------------------------------------
        # 1. Save the cleaned markdown text temporarily
        md_path = os.path.join(OUTPUT_DIR, f"{base_name}_latex.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_extracted_text)
        output_files.append(md_path)
        
        # 2. Use Pandoc to convert Markdown directly to DOCX
        docx_path = os.path.join(OUTPUT_DIR, f"{base_name}_converted.docx")
        
        # Enhanced Pandoc arguments to prevent line-wrapping and preserve complex tables
        pandoc_args = [
            '--from=markdown+tex_math_dollars+tex_math_single_backslash+pipe_tables+simple_tables+multiline_tables',
            '--wrap=none',
            '--columns=999'
        ]
        
        # Apply custom Word styling template if provided
        if reference_doc is not None:
            pandoc_args.append(f'--reference-doc={reference_doc.name}')
            
        pypandoc.convert_file(
            md_path, 
            'docx', 
            outputfile=docx_path,
            extra_args=pandoc_args
        )
        
        output_files.append(docx_path)
        
        return f"✅ Successfully processed {total_pages} pages.\nHigh-quality Word document generated. Headings, lists, tables, and equations have been properly preserved into native Word formats.", output_files
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return f"Error processing PDF: {str(e)}", None

# ==========================================
# GRADIO UI SETUP
# ==========================================
with gr.Blocks(title="DeepSeek-OCR PDF to Word") as demo:
    gr.Markdown("# 🔍 DeepSeek-OCR: Advanced PDF to Word Converter")
    gr.Markdown("Upload a **PDF document**. It will extract the text and preserve original formatting (Tables, Headings, and **Native Math Equations**) into a `.docx` Word file using Pandoc.")
    
    with gr.Row():
        with gr.Column():
            input_pdf = gr.File(file_count="single", type="filepath", label="1. Upload PDF File", file_types=[".pdf"])
            
            with gr.Group():
                gr.Markdown("### Style Options")
                reference_doc = gr.File(file_count="single", type="filepath", label="2. (Optional) Upload Word Style Template (.docx)", file_types=[".docx"])
                btn_gen_template = gr.Button("📥 Or Generate Auto CV Template", variant="secondary")
                
            pdf_model_size = gr.Radio(choices=["Tiny (512)", "Small (640)", "Base (1024)", "Gundam (High-Res)"], value="Gundam (High-Res)", label="Processing Resolution")
            btn_pdf = gr.Button("🚀 Convert PDF to Word", variant="primary")
        with gr.Column():
            out_text_pdf = gr.Textbox(label="Status / Console", lines=10)
            out_files_pdf = gr.File(label="Generated Files (Downloads)")
    
    # Connect the new template generator button
    btn_gen_template.click(fn=create_cv_word_template, outputs=[out_text_pdf, out_files_pdf])
    
    # Connect the main PDF to Word button
    btn_pdf.click(fn=process_pdf_to_word, inputs=[input_pdf, reference_doc, pdf_model_size], outputs=[out_text_pdf, out_files_pdf])

if __name__ == "__main__":
    print("Starting Web UI Server...")
    demo.launch(server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft())
