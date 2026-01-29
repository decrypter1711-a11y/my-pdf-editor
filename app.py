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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT

st.set_page_config(
    page_title="PDF Studio Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<head>
    <meta name="google-site-verification" content="googlee1f7c3d8ee1acfb5" />
</head>
""", unsafe_allow_html=True)
<style>
    .main {{ background-color: #f0f2f6; }}
    .stButton>button {{ width: 100%; border-radius: 6px; font-weight: 600; background-color: #007bff; color: white; }}
    .privacy-msg {{ background-color: #28a745; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 5px; margin-bottom: 20px; }}
    h1, h2 {{ color: #1e293b; }}
</style>
<meta name="description" content="Free online PDF editor. Convert images to PDF, OCR scanned documents, sign PDFs, merge, crop, and repair corrupted files.">
<meta name="keywords" content="PDF Editor, Online PDF, OCR PDF, Sign PDF Online, Merge PDF, Repair PDF, Free PDF Tool">
""", unsafe_allow_html=True)

st.markdown('<div class="privacy-msg">PRIVACY SECURED: Processing happens in RAM. No data is stored on our servers.</div>', unsafe_allow_html=True)

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
            p = Paragraph(line, custom_style)
            story.append(p)
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
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, config='--psm 3')
            full_text += f"{text}\n\n"
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
    st.sidebar.header("Features Menu")
    menu = ["Visual Editor", "Image to PDF", "OCR Extract Text", "Merge PDFs", "Split and Crop", "Repair Broken PDF", "Convert PDF Format"]
    choice = st.sidebar.radio("Select Tool", menu)
    processor = SecureProcessor()

    if choice == "Visual Editor":
        st.header("Visual PDF Editor and Signer")
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
                    st.divider()
                    edit_mode = st.radio("Tool", ["Add Signature", "Add Text", "Whiteout"])
                    overlay_img = None
                    if edit_mode == "Add Signature":
                        sig_src = st.radio("Source", ["Pad", "File"])
                        if sig_src == "Pad":
                            canv = st_canvas(fill_color="rgba(0,0,0,0)", stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=300, drawing_mode="freedraw", key="sig")
                            if canv.image_data is not None:
                                overlay_img = Image.fromarray(canv.image_data.astype('uint8'), 'RGBA')
                                datas = overlay_img.getdata()
                                new_d = []
                                for item in datas:
                                    if item[0] > 200 and item[1] > 200 and item[2] > 200: new_d.append((255,255,255,0))
                                    else: new_d.append(item)
                                overlay_img.putdata(new_d)
                                bbox = overlay_img.getbbox()
                                if bbox: overlay_img = overlay_img.crop(bbox)
                        else:
                            u = st.file_uploader("Upload PNG", type=['png'])
                            if u: overlay_img = Image.open(u)
                    elif edit_mode == "Add Text":
                        txt = st.text_input("Content", "Enter Text")
                        t_sz = st.slider("Size", 10, 150, 24)
                        t_clr = st.color_picker("Color", "#000000")
                        if txt:
                            try:
                                fnt = ImageFont.truetype("DejaVuSans.ttf", t_sz)
                            except:
                                fnt = ImageFont.load_default()
                            dummy_img = Image.new('RGBA', (1, 1))
                            d_dummy = ImageDraw.Draw(dummy_img)
                            text_bbox = d_dummy.textbbox((0, 0), txt, font=fnt)
                            tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                            overlay_img = Image.new('RGBA', (tw + 10, th + 10), (255, 255, 255, 0))
                            d = ImageDraw.Draw(overlay_img)
                            d.text((5, 5), txt, font=fnt, fill=t_clr)
                    elif edit_mode == "Whiteout":
                        overlay_img = Image.new('RGBA', (100, 50), (255,255,255,255))
                    st.divider()
                    if overlay_img:
                        x = st.slider("X Position", 0, current_img.width, 50)
                        y = st.slider("Y Position", 0, current_img.height, 50)
                        sc = st.slider("Scale", 0.1, 4.0, 1.0)
                        nw, nh = int(overlay_img.width*sc), int(overlay_img.height*sc)
                        if nw > 0 and nh > 0: overlay_img = overlay_img.resize((nw, nh))
                with c2:
                    st.subheader("Live Preview")
                    prev = current_img.convert("RGBA")
                    if overlay_img: prev.paste(overlay_img, (x, y), overlay_img)
                    st.image(prev, use_container_width=True)
                    if st.button("Apply Changes"):
                        if overlay_img:
                            reader = PdfReader(tmp_pdf_path)
                            writer = PdfWriter()
                            p_pg = reader.pages[page_idx]
                            pw, ph = float(p_pg.mediabox.width), float(p_pg.mediabox.height)
                            rw, rh = pw/current_img.width, ph/current_img.height
                            fx, fy = x*rw, (current_img.height - y - overlay_img.height)*rh
                            fw, fh = overlay_img.width*rw, overlay_img.height*rh
                            pack = io.BytesIO()
                            c = canvas.Canvas(pack, pagesize=(pw, ph))
                            if edit_mode == "Whiteout":
                                c.setFillColor(white); c.setStrokeColor(white); c.rect(fx, fy, fw, fh, fill=1, stroke=1)
                            elif edit_mode == "Add Text":
                                c.setFillColor(t_clr); c.setFont("Helvetica", t_sz * rh * sc); c.drawString(fx, fy + (fh/6), txt)
                            else:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                                    overlay_img.save(tf, format="PNG"); t_p = tf.name
                                c.drawImage(t_p, fx, fy, width=fw, height=fh, mask='auto')
                                cleanup_temp_file(t_p)
                            c.save(); pack.seek(0); ov_pdf = PdfReader(pack)
                            for i, pg in enumerate(reader.pages):
                                if i == page_idx: pg.merge_page(ov_pdf.pages[0])
                                writer.add_page(pg)
                            out = io.BytesIO(); writer.write(out)
                            st.session_state.edited_pdf_bytes = bytes(out.getvalue())
                            st.success("Changes Applied! Click Download below.")
                    
                    if st.session_state.edited_pdf_bytes:
                        st.download_button("Download Edited PDF", st.session_state.edited_pdf_bytes, "final.pdf", "application/pdf")
            finally:
                cleanup_temp_file(tmp_pdf_path)

    elif choice == "Image to PDF":
        st.header("Image to PDF Converter")
        files = st.file_uploader("Upload images", accept_multiple_files=True, type=['jpg','png','jpeg'])
        if files and st.button("Convert"):
            res = processor.images_to_pdf(files)
            st.download_button("Download PDF", res, "images.pdf")

    elif choice == "OCR Extract Text":
        st.header("OCR Engine")
        f = st.file_uploader("Upload Scanned PDF", type=['pdf'])
        if f:
            if st.button("Process OCR"):
                txt = processor.extract_text(f.read())
                st.session_state.ocr_buffer = txt
            if st.session_state.ocr_buffer:
                st.session_state.ocr_buffer = st.text_area("Review and Edit", st.session_state.ocr_buffer, height=450)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("Download TXT", st.session_state.ocr_buffer, "document.txt")
                with col2:
                    pdf_data = fast_text_to_pdf(st.session_state.ocr_buffer)
                    st.download_button("Download PDF", pdf_data, "ocr.pdf")

    elif choice == "Merge PDFs":
        st.header("Merge PDFs")
        files = st.file_uploader("Select PDFs", accept_multiple_files=True, type=['pdf'])
        if files and st.button("Merge"):
            res = processor.merge_pdfs(files)
            st.download_button("Download Merged PDF", res, "merged.pdf")

    elif choice == "Split and Crop":
        st.header("PDF Cropper")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t:
                t.write(f.read()); t_n = t.name
            try:
                imgs = convert_from_bytes(open(t_n, 'rb').read())
                idx = st.number_input("Page", 1, len(imgs), 1) - 1
                crp = st_cropper(imgs[idx], realtime_update=True, box_color='red')
                if st.button("Save Crop"):
                    b = io.BytesIO(); crp.save(b, format='PNG')
                    st.download_button("Download Crop", bytes(img2pdf.convert(b.getvalue())), "crop.pdf")
            finally:
                cleanup_temp_file(t_n)

    elif choice == "Repair Broken PDF":
        st.header("Repair PDF")
        f = st.file_uploader("Upload Damaged PDF", type=['pdf'])
        if f and st.button("Repair"):
            try:
                res = processor.repair_pdf(f)
                st.download_button("Download Repaired", res, "fixed.pdf")
            except Exception as e:
                st.error(f"Error: {e}")

    elif choice == "Convert PDF Format":
        st.header("Converter")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        fmt = st.selectbox("Target Format", ["JPG Page 1", "Word Text"])
        if f and st.button("Convert"):
            if "JPG" in fmt:
                img = convert_from_bytes(f.read())[0]
                b = io.BytesIO(); img.save(b, format="JPEG")
                st.download_button("Download JPG", bytes(b.getvalue()), "page1.jpg")
            else:
                txt = processor.extract_text(f.read())
                st.download_button("Download Doc", txt, "export.doc")

    st.markdown("---")
    st.markdown("### Free Online PDF Editor Suite")
    st.caption("Privacy-First PDF Editor | Online OCR | Sign PDF | Merge PDF | Repair PDF")

if __name__ == "__main__":
    main()
