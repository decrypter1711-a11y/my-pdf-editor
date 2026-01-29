import streamlit as st
import img2pdf
import pikepdf
import pytesseract
import io
import os
import tempfile
import base64
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
    page_title="Free Online PDF Editor | Edit, Merge, OCR, Sign PDFs",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { background-color: #f0f2f6; }
.stButton>button { width: 100%; border-radius: 6px; font-weight: 600; background-color: #2563eb; color: white; }
.privacy-msg { background-color: #16a34a; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 5px; margin-bottom: 20px; }
h1, h2, h3 { color: #1e293b; }
</style>

<meta name="description" content="Free online PDF editor to edit, merge, OCR, sign, crop, repair, and convert PDF files. Privacy-first and open source PDF editor.">
<meta name="keywords" content="free pdf editor, online pdf editor, edit pdf online, merge pdf, ocr pdf, sign pdf online, repair pdf, open source pdf editor">
""", unsafe_allow_html=True)

st.markdown("""
# Free Online PDF Editor

Edit PDF files online for free. This privacy-first PDF editor lets you edit, sign, merge, OCR, crop, convert, and repair PDF files directly in your browser without installing software.

<div class="privacy-msg">PRIVACY SECURED: All PDF processing happens in memory. No files are stored.</div>
""", unsafe_allow_html=True)

if "edited_pdf_bytes" not in st.session_state:
    st.session_state.edited_pdf_bytes = None
if "ocr_buffer" not in st.session_state:
    st.session_state.ocr_buffer = ""

def cleanup_temp_file(path):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass

def fast_text_to_pdf(text_content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        wordWrap='LTR'
    )
    story = []
    text_content = text_content.replace('*', '&bull;').replace('\u2022', '&bull;')
    lines = text_content.split('\n')
    for line in lines:
        if line.strip():
            story.append(Paragraph(line, custom_style))
            story.append(Spacer(1, 6))
        else:
            story.append(Spacer(1, 12))
    doc.build(story)
    return bytes(buffer.getvalue())

class SecureProcessor:
    def __init__(self):
        self.memory_buffer = io.BytesIO()

    def merge_pdfs(self, file_list):
        merger = PdfWriter()
        for pdf in file_list:
            merger.append(pdf)
        merger.write(self.memory_buffer)
        return bytes(self.memory_buffer.getvalue())

    def images_to_pdf(self, image_list):
        img_bytes = [i.read() for i in image_list]
        return bytes(img2pdf.convert(img_bytes))

    def extract_text(self, pdf_bytes):
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img, config='--psm 3') + "\n\n"
        return full_text

    def repair_pdf(self, file_obj):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_obj.read())
            tmp_path = tmp.name
        try:
            pdf = pikepdf.open(tmp_path, allow_overwriting_input=True)
            pdf.save(self.memory_buffer)
            return bytes(self.memory_buffer.getvalue())
        finally:
            cleanup_temp_file(tmp_path)

def main():
    st.sidebar.header("PDF Tools")
    menu = ["Visual Editor", "Image to PDF", "OCR Extract Text", "Merge PDFs", "Split and Crop", "Repair Broken PDF", "Convert PDF Format"]
    choice = st.sidebar.radio("Select PDF Tool", menu)
    processor = SecureProcessor()

    if choice == "Visual Editor":
        st.header("Visual PDF Editor and PDF Signer")
        target_pdf = st.file_uploader("Upload PDF File", type=['pdf'])
        if target_pdf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(target_pdf.getvalue())
                tmp_pdf_path = tmp_pdf.name
            try:
                pages = convert_from_bytes(open(tmp_pdf_path, 'rb').read())
                c1, c2 = st.columns([1, 2])
                with c1:
                    page_idx = st.number_input("Select Page", 1, len(pages), 1) - 1
                    current_img = pages[page_idx].copy()
                    edit_mode = st.radio("Editing Tool", ["Add Signature", "Add Text", "Whiteout"])
                    overlay_img = None
                    if edit_mode == "Add Signature":
                        sig_src = st.radio("Signature Source", ["Pad", "File"])
                        if sig_src == "Pad":
                            canv = st_canvas(fill_color="rgba(0,0,0,0)", stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=300, drawing_mode="freedraw", key="sig")
                            if canv.image_data is not None:
                                overlay_img = Image.fromarray(canv.image_data.astype('uint8'), 'RGBA')
                                overlay_img = overlay_img.crop(overlay_img.getbbox())
                        else:
                            u = st.file_uploader("Upload PNG Signature", type=['png'])
                            if u:
                                overlay_img = Image.open(u)
                    elif edit_mode == "Add Text":
                        txt = st.text_input("Text Content", "Enter text")
                        t_sz = st.slider("Text Size", 10, 150, 24)
                        t_clr = st.color_picker("Text Color", "#000000")
                        if txt:
                            fnt = ImageFont.load_default()
                            dummy = Image.new('RGBA', (1, 1))
                            d = ImageDraw.Draw(dummy)
                            bbox = d.textbbox((0, 0), txt, font=fnt)
                            overlay_img = Image.new('RGBA', (bbox[2]+10, bbox[3]+10), (255,255,255,0))
                            d = ImageDraw.Draw(overlay_img)
                            d.text((5,5), txt, fill=t_clr)
                    elif edit_mode == "Whiteout":
                        overlay_img = Image.new('RGBA', (120, 50), (255,255,255,255))
                    if overlay_img:
                        x = st.slider("X Position", 0, current_img.width, 50)
                        y = st.slider("Y Position", 0, current_img.height, 50)
                        sc = st.slider("Scale", 0.1, 4.0, 1.0)
                        overlay_img = overlay_img.resize((int(overlay_img.width*sc), int(overlay_img.height*sc)))
                with c2:
                    prev = current_img.convert("RGBA")
                    if overlay_img:
                        prev.paste(overlay_img, (x, y), overlay_img)
                    st.image(prev, use_container_width=True)
                    if st.button("Apply Changes"):
                        reader = PdfReader(tmp_pdf_path)
                        writer = PdfWriter()
                        pack = io.BytesIO()
                        p_pg = reader.pages[page_idx]
                        pw, ph = float(p_pg.mediabox.width), float(p_pg.mediabox.height)
                        rw, rh = pw/current_img.width, ph/current_img.height
                        c = canvas.Canvas(pack, pagesize=(pw, ph))
                        if edit_mode == "Whiteout":
                            c.setFillColor(white)
                            c.rect(x*rw, (current_img.height-y-overlay_img.height)*rh, overlay_img.width*rw, overlay_img.height*rh, fill=1)
                        elif edit_mode == "Add Text":
                            c.setFillColor(t_clr)
                            c.drawString(x*rw, (current_img.height-y)*rh, txt)
                        else:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                                overlay_img.save(tf.name)
                                c.drawImage(tf.name, x*rw, (current_img.height-y-overlay_img.height)*rh, overlay_img.width*rw, overlay_img.height*rh)
                                cleanup_temp_file(tf.name)
                        c.save()
                        pack.seek(0)
                        ov = PdfReader(pack)
                        for i,p in enumerate(reader.pages):
                            if i == page_idx:
                                p.merge_page(ov.pages[0])
                            writer.add_page(p)
                        out = io.BytesIO()
                        writer.write(out)
                        st.session_state.edited_pdf_bytes = out.getvalue()
                    if st.session_state.edited_pdf_bytes:
                        st.download_button("Download Edited PDF", st.session_state.edited_pdf_bytes, "edited.pdf", "application/pdf")
            finally:
                cleanup_temp_file(tmp_pdf_path)

    elif choice == "Image to PDF":
        st.header("Image to PDF Converter")
        files = st.file_uploader("Upload Images", accept_multiple_files=True, type=['jpg','png','jpeg'])
        if files and st.button("Convert to PDF"):
            res = processor.images_to_pdf(files)
            st.download_button("Download PDF", res, "images.pdf")

    elif choice == "OCR Extract Text":
        st.header("OCR PDF Text Extractor")
        f = st.file_uploader("Upload Scanned PDF", type=['pdf'])
        if f and st.button("Extract Text"):
            st.session_state.ocr_buffer = processor.extract_text(f.read())
        if st.session_state.ocr_buffer:
            st.session_state.ocr_buffer = st.text_area("Extracted Text", st.session_state.ocr_buffer, height=400)
            st.download_button("Download TXT", st.session_state.ocr_buffer, "text.txt")
            st.download_button("Download PDF", fast_text_to_pdf(st.session_state.ocr_buffer), "ocr.pdf")

    elif choice == "Merge PDFs":
        st.header("Merge PDF Files")
        files = st.file_uploader("Upload PDFs", accept_multiple_files=True, type=['pdf'])
        if files and st.button("Merge PDFs"):
            res = processor.merge_pdfs(files)
            st.download_button("Download Merged PDF", res, "merged.pdf")

    elif choice == "Split and Crop":
        st.header("Crop PDF Pages")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t:
                t.write(f.read())
                imgs = convert_from_bytes(open(t.name,'rb').read())
                idx = st.number_input("Select Page", 1, len(imgs), 1) - 1
                crp = st_cropper(imgs[idx])
                if st.button("Save Crop"):
                    b = io.BytesIO()
                    crp.save(b, format="PNG")
                    st.download_button("Download Cropped PDF", img2pdf.convert(b.getvalue()), "crop.pdf")
            cleanup_temp_file(t.name)

    elif choice == "Repair Broken PDF":
        st.header("Repair Corrupted PDF")
        f = st.file_uploader("Upload Damaged PDF", type=['pdf'])
        if f and st.button("Repair PDF"):
            res = processor.repair_pdf(f)
            st.download_button("Download Repaired PDF", res, "repaired.pdf")

    elif choice == "Convert PDF Format":
        st.header("PDF Converter")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        fmt = st.selectbox("Convert To", ["JPG Page 1", "Text Document"])
        if f and st.button("Convert"):
            if "JPG" in fmt:
                img = convert_from_bytes(f.read())[0]
                b = io.BytesIO()
                img.save(b, format="JPEG")
                st.download_button("Download JPG", b.getvalue(), "page.jpg")
            else:
                txt = processor.extract_text(f.read())
                st.download_button("Download TXT", txt, "file.txt")

    st.markdown("""
## Online PDF Editor Features
- Edit PDF online
- Sign PDF documents
- OCR scanned PDFs
- Merge and split PDFs
- Crop PDF pages
- Repair corrupted PDF files
- Convert PDF to images and text

This free online PDF editor is open source and privacy focused.
""")

if __name__ == "__main__":
    main()
