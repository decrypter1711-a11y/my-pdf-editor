import streamlit as st
import img2pdf
import pikepdf
import pytesseract
import io
import os
import re
import tempfile
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import white, black
from streamlit_drawable_canvas import st_canvas
from streamlit_cropper import st_cropper
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

st.set_page_config(
    page_title="PDF Studio Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { background-color: #f0f2f6; }
.stButton>button { width: 100%; border-radius: 6px; font-weight: 700; background-color: #007bff; color: white; border: none; padding: 10px; transition: 0.3s; }
.stButton>button:hover { background-color: #0056b3; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
.privacy-msg { background-color: #28a745; color: white; padding: 15px; text-align: center; font-weight: 900; border-radius: 8px; margin-bottom: 25px; border: 2px solid #1e7e34; }
h1, h2, h3 { color: #1e293b; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
@media (max-width: 600px) {
    .main { padding: 10px !important; }
    .stColumns { flex-direction: column !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="privacy-msg">SECURE RAM-ONLY VOLATILE ARCHITECTURE - ZERO PERSISTENCE PROTOCOL</div>', unsafe_allow_html=True)

if "edited_pdf_bytes" not in st.session_state:
    st.session_state.edited_pdf_bytes = None
if "active_file_hash" not in st.session_state:
    st.session_state.active_file_hash = None
if "file_uploaded_once" not in st.session_state:
    st.session_state.file_uploaded_once = False
if "ocr_result_pdf" not in st.session_state:
    st.session_state.ocr_result_pdf = None
if "ocr_text_preview" not in st.session_state:
    st.session_state.ocr_text_preview = ""

def purge_temporary_resource(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

class CoreEngine:
    def consolidate_pdf_entities(self, sequence):
        writer = PdfWriter()
        for f in sequence:
            reader = PdfReader(f)
            for p in reader.pages:
                writer.add_page(p)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def raster_to_vector_pdf(self, image_sequence):
        payload = []
        for img in image_sequence:
            img.seek(0)
            payload.append(img.read())
        return img2pdf.convert(payload)

    def linguistic_extraction(self, stream):
        pages = convert_from_bytes(stream)
        text = ""
        for p in pages:
            seg = pytesseract.image_to_string(p, config="--psm 3")
            seg = re.sub(r'^\s*[\-_]\s+', '• ', seg, flags=re.MULTILINE)
            text += seg + "\n"
        return text

    def generate_searchable_hocr(self, stream):
        pages = convert_from_bytes(stream)
        writer = PdfWriter()
        for p in pages:
            layer = pytesseract.image_to_pdf_or_hocr(p, extension="pdf", config="--psm 3")
            r = PdfReader(io.BytesIO(layer))
            writer.add_page(r.pages[0])
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def structural_restoration(self, uploaded):
        uploaded.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(uploaded.read())
            path = f.name
        try:
            pdf = pikepdf.open(path, allow_overwriting_input=True)
            out = io.BytesIO()
            pdf.save(out)
            return out.getvalue()
        finally:
            purge_temporary_resource(path)

def main_orchestrator():
    st.sidebar.header("PDF Studio Controller")
    interaction_mode = st.sidebar.radio(
        "Executive Modules",
        [
            "Visual Editor",
            "Image to PDF",
            "OCR Extract Text",
            "Merge PDFs",
            "Split and Crop",
            "Repair Broken PDF",
            "Convert PDF Format",
        ],
    )

    processor = CoreEngine()

    if interaction_mode == "Visual Editor":
        st.header("Visual Manipulation Layer")
        uplink = st.file_uploader("Source PDF Transaction", type=["pdf"])

        if uplink:
            stream_identity = uplink.name + str(uplink.size)
            if st.session_state.active_file_hash != stream_identity:
                st.session_state.active_file_hash = stream_identity
                st.session_state.edited_pdf_bytes = None
                st.session_state.file_uploaded_once = True

        if uplink and st.session_state.edited_pdf_bytes is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(uplink.getvalue())
                session_path = f.name
        else:
            session_path = None

        if session_path:
            try:
                frames = convert_from_bytes(open(session_path, "rb").read())
                col1, col2 = st.columns([1, 2])

                with col1:
                    idx = st.number_input("Page", 1, len(frames), 1) - 1
                    mode = st.radio("Modification Protocol", ["Add Text", "Whiteout"])
                    text = st.text_input("Text", "Sample Text")
                    size = st.slider("Size", 10, 200, 30)
                    color = st.color_picker("Color", "#000000")
                    x = st.slider("X", 0, frames[idx].width, 100)
                    y = st.slider("Y", 0, frames[idx].height, 100)

                with col2:
                    preview = frames[idx].convert("RGBA")
                    draw = ImageDraw.Draw(preview)
                    if mode == "Add Text":
                        try:
                            font = ImageFont.truetype("DejaVuSans.ttf", size)
                        except:
                            font = ImageFont.load_default()
                        draw.text((x, y), text, fill=color, font=font)
                    else:
                        draw.rectangle((x, y, x + 150, y + 60), fill="white")
                    st.image(preview, use_container_width=True)

                    if st.button("Execute Injection Protocol"):
                        reader = PdfReader(session_path)
                        writer = PdfWriter()
                        page = reader.pages[idx]
                        w = float(page.mediabox.width)
                        h = float(page.mediabox.height)
                        overlay = io.BytesIO()
                        c = canvas.Canvas(overlay, pagesize=(w, h))
                        if mode == "Add Text":
                            c.setFillColor(color)
                            c.setFont("Helvetica", size)
                            c.drawString(x, h - y - size, text)
                        else:
                            c.setFillColor(white)
                            c.rect(x, h - y - 60, 150, 60, fill=1)
                        c.save()
                        overlay.seek(0)
                        o = PdfReader(overlay)
                        page.merge_page(o.pages[0])
                        for i, p in enumerate(reader.pages):
                            writer.add_page(page if i == idx else p)
                        out = io.BytesIO()
                        writer.write(out)
                        st.session_state.edited_pdf_bytes = out.getvalue()
                        st.success("Delta Injection Synchronized")
            finally:
                purge_temporary_resource(session_path)

        if st.session_state.edited_pdf_bytes:
            st.download_button(
                "Export Modified PDF Artifact",
                data=io.BytesIO(st.session_state.edited_pdf_bytes).getvalue(),
                file_name="modified_output.pdf",
                mime="application/pdf",
                key="download_final_pdf",
            )

    elif interaction_mode == "Image to PDF":
        imgs = st.file_uploader("Visual Assets", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if imgs and st.button("Generate Encapsulation"):
            pdf = processor.raster_to_vector_pdf(imgs)
            st.download_button("Export PDF Entity", pdf, "collection_archive.pdf")

    elif interaction_mode == "OCR Extract Text":
        f = st.file_uploader("Analog PDF Stream", type=["pdf"])
        if f and st.button("Initiate Neural Scan"):
            data = f.read()
            st.session_state.ocr_text_preview = processor.linguistic_extraction(data)
            st.session_state.ocr_result_pdf = processor.generate_searchable_hocr(data)
        if st.session_state.ocr_text_preview:
            st.text_area("Linguistic Buffer", st.session_state.ocr_text_preview, height=350)
            st.download_button("Export Literal TXT", st.session_state.ocr_text_preview, "linguistic_data.txt")
            st.download_button("Export Hybrid Searchable PDF", st.session_state.ocr_result_pdf, "searchable_intel.pdf")

    elif interaction_mode == "Merge PDFs":
        files = st.file_uploader("PDF Fragments", type=["pdf"], accept_multiple_files=True)
        if files and st.button("Execute Consolidation"):
            merged = processor.consolidate_pdf_entities(files)
            st.download_button("Export Consolidated Stream", merged, "unified_system_data.pdf")

    elif interaction_mode == "Split and Crop":
        f = st.file_uploader("Geometry PDF", type=["pdf"])
        if f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t:
                t.write(f.read())
                path = t.name
            try:
                pages = convert_from_bytes(open(path, "rb").read())
                i = st.number_input("Page", 1, len(pages), 1) - 1
                crop = st_cropper(pages[i], realtime_update=True)
                if st.button("Commit Partition"):
                    buf = io.BytesIO()
                    crop.save(buf, format="PNG")
                    st.download_button("Export Partition PDF", img2pdf.convert(buf.getvalue()), "spatial_partition.pdf")
            finally:
                purge_temporary_resource(path)

    elif interaction_mode == "Repair Broken PDF":
        f = st.file_uploader("Damaged Binary Object", type=["pdf"])
        if f and st.button("Initiate Restoration"):
            repaired = processor.structural_restoration(f)
            st.download_button("Export Restored Entity", repaired, "restored_system_data.pdf")

    elif interaction_mode == "Convert PDF Format":
        f = st.file_uploader("Origin PDF", type=["pdf"])
        target = st.selectbox("Destination Schema", ["JPG Raster Page 1", "Word Processor Text"])
        if f and st.button("Commence Polymorphism"):
            if "JPG" in target:
                img = convert_from_bytes(f.read())[0]
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                st.download_button("Export Raster JPG", buf.getvalue(), "rasterized_page.jpg")
            else:
                text = processor.linguistic_extraction(f.read())
                st.download_button("Export Document Object", text, "polymorphic_export.doc")

    st.markdown("---")
    st.caption("ZERO-TRUST DATA PROCESSING | CLIENT-SIDE RAM VOLATILITY | HARDENED PDF MANIPULATION")

if __name__ == "__main__":
    main_orchestrator()
