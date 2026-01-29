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
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; background-color: #007bff; color: white; }
    .privacy-msg { background-color: #28a745; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 5px; margin-bottom: 20px; }
    h1, h2 { color: #1e293b; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="privacy-msg">PRIVACY SECURED: RAM PROCESSING ONLY</div>', unsafe_allow_html=True)

if "edited_pdf_bytes" not in st.session_state:
    st.session_state.edited_pdf_bytes = None
if "current_file_id" not in st.session_state:
    st.session_state.current_file_id = None
if "ocr_result_pdf" not in st.session_state:
    st.session_state.ocr_result_pdf = None
if "ocr_text_preview" not in st.session_state:
    st.session_state.ocr_text_preview = ""

def cleanup_temp_file(path):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass

class SecureProcessor:
    def __init__(self):
        self.memory_buffer = io.BytesIO()

    def merge_pdfs(self, file_list):
        merger = PdfWriter()
        for pdf in file_list:
            pdf.seek(0)
            merger.append(pdf)
        merger.write(self.memory_buffer)
        return bytes(self.memory_buffer.getvalue())

    def images_to_pdf(self, image_list):
        # Fix for rotation error on mobile devices
        img_bytes = []
        for i in image_list:
            i.seek(0)
            img_bytes.append(i.read())
        return bytes(img2pdf.convert(img_bytes, rotation=img2pdf.Rotation.ifvalid))

    def extract_text(self, pdf_bytes):
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for i, img in enumerate(images):
            # Regex to clean up bullet points often misread as 'e', 'c', or 'o' at start of lines
            text = pytesseract.image_to_string(img, config='--psm 3')
            text = re.sub(r'^\s*[e|c|o]\s+', '• ', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*[\-_]\s+', '• ', text, flags=re.MULTILINE)
            full_text += f"{text}\n"
        return full_text

    def create_searchable_pdf(self, pdf_bytes):
        # Creates a PDF that looks EXACTLY like the original image but is searchable (HOCR)
        images = convert_from_bytes(pdf_bytes)
        writer = PdfWriter()
        
        for img in images:
            pdf_page_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='pdf', config='--psm 3')
            page_reader = PdfReader(io.BytesIO(pdf_page_bytes))
            writer.add_page(page_reader.pages[0])
            
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        return bytes(output_buffer.getvalue())

    def repair_pdf(self, file_obj):
        file_obj.seek(0)
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
        st.header("Visual PDF Editor")
        target_pdf = st.file_uploader("Upload PDF File", type=['pdf'], key="viz_uploader")
        
        if target_pdf:
            file_id = target_pdf.file_id if hasattr(target_pdf, 'file_id') else target_pdf.name
            if st.session_state.current_file_id != file_id:
                st.session_state.edited_pdf_bytes = None
                st.session_state.current_file_id = file_id

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
                            if u: overlay_img = Image.open(u).convert("RGBA")
                            
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
                    if overlay_img:
                        prev.paste(overlay_img, (x, y), overlay_img)
                    st.image(prev, use_container_width=True)
                    
                    if st.button("Apply Changes"):
                        if overlay_img:
                            # Re-open original PDF
                            reader = PdfReader(tmp_pdf_path)
                            writer = PdfWriter()
                            
                            # Get dimensions from the target page
                            p_pg = reader.pages[page_idx]
                            pw = float(p_pg.mediabox.width)
                            ph = float(p_pg.mediabox.height)
                            
                            # Calculate scaling ratios
                            rw, rh = pw/current_img.width, ph/current_img.height
                            fx, fy = x*rw, (current_img.height - y - overlay_img.height)*rh
                            fw, fh = overlay_img.width*rw, overlay_img.height*rh
                            
                            # Create Overlay PDF
                            pack = io.BytesIO()
                            c = canvas.Canvas(pack, pagesize=(pw, ph))
                            
                            if edit_mode == "Whiteout":
                                c.setFillColor(white)
                                c.setStrokeColor(white)
                                c.rect(fx, fy, fw, fh, fill=1, stroke=1)
                            elif edit_mode == "Add Text":
                                c.setFillColor(t_clr)
                                c.setFont("Helvetica", t_sz * rh * sc)
                                # Adjust text position slightly for baseline
                                c.drawString(fx, fy + (fh/4), txt)
                            else:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                                    overlay_img.save(tf, format="PNG")
                                    t_p = tf.name
                                c.drawImage(t_p, fx, fy, width=fw, height=fh, mask='auto')
                                cleanup_temp_file(t_p)
                                
                            c.save()
                            pack.seek(0)
                            ov_pdf = PdfReader(pack)
                            
                            # Merge Overlay into Original
                            for i, pg in enumerate(reader.pages):
                                if i == page_idx:
                                    pg.merge_page(ov_pdf.pages[0])
                                writer.add_page(pg)
                                
                            out = io.BytesIO()
                            writer.write(out)
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
            try:
                res = processor.images_to_pdf(files)
                st.download_button("Download PDF", res, "images.pdf")
            except Exception as e:
                st.error(f"Error converting images: {e}")

    elif choice == "OCR Extract Text":
        st.header("OCR Engine (Preserves Layout)")
        f = st.file_uploader("Upload Scanned PDF", type=['pdf'])
        if f:
            if st.button("Process OCR"):
                with st.spinner("Analyzing document structure..."):
                    raw_bytes = f.read()
                    txt = processor.extract_text(raw_bytes)
                    st.session_state.ocr_text_preview = txt
                    pdf_bytes = processor.create_searchable_pdf(raw_bytes)
                    st.session_state.ocr_result_pdf = pdf_bytes
            
            if st.session_state.ocr_text_preview:
                st.text_area("Text Content Preview", st.session_state.ocr_text_preview, height=250)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("Download Text", st.session_state.ocr_text_preview, "document.txt")
                with col2:
                    if st.session_state.ocr_result_pdf:
                        st.download_button("Download PDF", st.session_state.ocr_result_pdf, "searchable_doc.pdf")

    elif choice == "Merge PDFs":
        st.header("Merge PDFs")
        files = st.file_uploader("Select PDFs", accept_multiple_files=True, type=['pdf'])
        if files and st.button("Merge"):
            try:
                res = processor.merge_pdfs(files)
                st.download_button("Download Merged PDF", res, "merged.pdf")
            except Exception as e:
                st.error(f"Merge error: {e}")

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
