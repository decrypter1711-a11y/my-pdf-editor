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
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="PDF Studio Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .privacy-msg { background-color: #ff4b4b; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="privacy-msg">YOUR DATA IS NOT SAVED. ALL FILES ARE WIPED AFTER PROCESSING.</div>', unsafe_allow_html=True)

def cleanup_temp_file(path):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass

def fast_text_to_pdf(text_content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for line in text_content.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles["Normal"]))
        else:
            story.append(Spacer(1, 12))
    doc.build(story)
    buffer.seek(0)
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
            text = pytesseract.image_to_string(img)
            full_text += f"--- Page {i+1} ---\n{text}\n\n"
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
    st.sidebar.header("Navigation")
    menu = ["Visual Editor", "Image to PDF", "OCR Extract Text", "Merge PDFs", "Split and Crop", "Repair Broken PDF", "Convert PDF Format"]
    choice = st.sidebar.radio("Select Tool", menu)
    processor = SecureProcessor()

    if choice == "Visual Editor":
        st.header("Visual Editor")
        target_pdf = st.file_uploader("Upload PDF", type=['pdf'])
        if target_pdf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(target_pdf.getvalue())
                tmp_pdf_path = tmp_pdf.name
            try:
                pages = convert_from_bytes(open(tmp_pdf_path, 'rb').read())
                c1, c2 = st.columns([1, 2])
                with c1:
                    page_idx = st.number_input("Page", 1, len(pages), 1) - 1
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
                        txt = st.text_input("Text Content", "Enter Text")
                        t_sz = st.slider("Text Size", 10, 100, 24)
                        t_clr = st.color_picker("Color", "#000000")
                        if txt:
                            overlay_img = Image.new('RGBA', (len(txt)*t_sz, t_sz+10), (255,255,255,0))
                            d = ImageDraw.Draw(overlay_img)
                            try: fnt = ImageFont.truetype("DejaVuSans.ttf", t_sz)
                            except: fnt = ImageFont.load_default()
                            d.text((0,0), txt, font=fnt, fill=t_clr)
                            bbox = overlay_img.getbbox()
                            if bbox: overlay_img = overlay_img.crop(bbox)
                    elif edit_mode == "Whiteout":
                        overlay_img = Image.new('RGBA', (100, 50), (255,255,255,255))
                    st.divider()
                    if overlay_img:
                        x = st.slider("X Position", 0, current_img.width, 50)
                        y = st.slider("Y Position", 0, current_img.height, 50)
                        sc = st.slider("Scale", 0.1, 5.0, 1.0)
                        nw, nh = int(overlay_img.width*sc), int(overlay_img.height*sc)
                        if nw > 0 and nh > 0: overlay_img = overlay_img.resize((nw, nh))
                with c2:
                    st.subheader("Live Preview")
                    prev = current_img.convert("RGBA")
                    if overlay_img: prev.paste(overlay_img, (x, y), overlay_img)
                    st.image(prev, use_container_width=True)
                    if st.button("Apply and Download"):
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
                                c.setFillColor(t_clr); c.setFont("Helvetica", t_sz*rh); c.drawString(fx, fy + (fh/4), txt)
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
                            st.download_button("Download Edited PDF", bytes(out.getvalue()), "edited.pdf", "application/pdf")
            finally:
                cleanup_temp_file(tmp_pdf_path)

    elif choice == "Image to PDF":
        st.header("Images to PDF")
        files = st.file_uploader("Upload Images", accept_multiple_files=True, type=['jpg','png','jpeg'])
        if files and st.button("Convert"):
            res = processor.images_to_pdf(files)
            st.download_button("Download PDF", res, "converted.pdf", "application/pdf")

    elif choice == "OCR Extract Text":
        st.header("Extract Text")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            if st.button("Process PDF for OCR"):
                with st.spinner("Extracting..."):
                    txt = processor.extract_text(f.read())
                    st.session_state['ocr_buffer'] = txt

            if 'ocr_buffer' in st.session_state:
                st.success("Extraction Complete")
                final_text = st.text_area("Review and Edit Text Content", st.session_state['ocr_buffer'], height=400)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("Download as TXT", final_text, "extracted.txt", "text/plain")
                with col2:
                    pdf_data = fast_text_to_pdf(final_text)
                    st.download_button("Download as PDF", pdf_data, "extracted.pdf", "application/pdf")

    elif choice == "Merge PDFs":
        st.header("Merge PDFs")
        files = st.file_uploader("Upload Files", accept_multiple_files=True, type=['pdf'])
        if files and st.button("Merge"):
            res = processor.merge_pdfs(files)
            st.download_button("Download Merged", res, "merged.pdf", "application/pdf")

    elif choice == "Split and Crop":
        st.header("Crop PDF")
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
                    st.download_button("Download Cropped PDF", bytes(img2pdf.convert(b.getvalue())), "crop.pdf", "application/pdf")
            finally:
                cleanup_temp_file(t_n)

    elif choice == "Repair Broken PDF":
        st.header("Repair PDF")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f and st.button("Fix"):
            res = processor.repair_pdf(f)
            st.download_button("Download Repaired", res, "repaired.pdf", "application/pdf")

    elif choice == "Convert PDF Format":
        st.header("Converter")
        f = st.file_uploader("Upload PDF", type=['pdf'])
        fmt = st.selectbox("To Format", ["JPG Page 1", "Word Text"])
        if f and st.button("Convert"):
            if fmt == "JPG Page 1":
                img = convert_from_bytes(f.read())[0]
                b = io.BytesIO(); img.save(b, format="JPEG")
                st.download_button("Download JPG", bytes(b.getvalue()), "page1.jpg")
            else:
                txt = processor.extract_text(f.read())
                st.download_button("Download Text", txt, "export.doc")

if __name__ == "__main__":
    main()
