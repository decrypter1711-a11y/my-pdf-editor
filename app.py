import streamlit as st
import img2pdf
import pikepdf
import pytesseract
import io
import os
import tempfile
import base64
import re
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import white, black
from streamlit_drawable_canvas import st_canvas
from streamlit_cropper import st_cropper
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch

st.set_page_config(page_title="PDF Studio Pro", layout="wide", initial_sidebar_state="auto")

st.markdown("""
<style>
    .main { background-color: #f0f2f6; padding: 1rem; }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        font-weight: 600;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        margin: 0.5rem 0;
    }
    .privacy-msg { 
        background-color: #ff4b4b; 
        color: white; 
        padding: 12px; 
        text-align: center; 
        font-weight: bold; 
        border-radius: 8px;
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }
    .stRadio > label { font-weight: 600; font-size: 1rem; }
    .stFileUploader > label { font-weight: 600; font-size: 1rem; }
    .stNumberInput > label { font-weight: 600; }
    .stSlider > label { font-weight: 600; }
    .stTextInput > label { font-weight: 600; }
    .stTextArea > label { font-weight: 600; }
    
    @media (max-width: 768px) {
        .main { padding: 0.5rem; }
        .stButton>button { font-size: 0.9rem; padding: 0.6rem; }
        .privacy-msg { font-size: 0.85rem; padding: 10px; }
        h1 { font-size: 1.5rem; }
        h2 { font-size: 1.2rem; }
        h3 { font-size: 1rem; }
        .stImage { margin: 0.5rem 0; }
    }
    
    .image-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .image-item {
        position: relative;
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 0.5rem;
        background: white;
    }
    
    @media (max-width: 768px) {
        .image-grid {
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="privacy-msg">YOUR DATA IS NOT SAVED. ALL FILES ARE WIPED AFTER PROCESSING.</div>', unsafe_allow_html=True)

def cleanup_temp_file(path):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass

def clean_ocr_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.replace(' J ', ' J')
        line = re.sub(r'\bJ\s+([a-z])', r'J\1', line)
        
        line = re.sub(r'(\d)\s*O\s*(\d)', r'\g<1>0\g<2>', line)
        line = re.sub(r'(\d)\s*O\s*O', r'\g<1>00', line)
        line = re.sub(r'(\d)\s*O\b', r'\g<1>0', line)
        
        line = re.sub(r'[¢*•●◆▪◦⚫]', '-', line)
        
        line = line.replace('@example.com I Phone', '@example.com | Phone')
        line = re.sub(r'\s+I\s+Phone', ' | Phone', line)
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def fast_text_to_pdf(text_content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=1*inch, rightMargin=1*inch, topMargin=1*inch, bottomMargin=1*inch)
    styles = getSampleStyleSheet()
    
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    
    story = []
    lines = text_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 12))
            continue
        
        try:
            clean_line = line.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            story.append(Paragraph(clean_line, custom_style))
        except:
            ascii_line = ''.join(c if ord(c) < 128 else ' ' for c in line)
            story.append(Paragraph(ascii_line, custom_style))
    
    doc.build(story)
    buffer.seek(0)
    return bytes(buffer.getvalue())

def enhanced_ocr_extraction(pdf_bytes):
    images = convert_from_bytes(pdf_bytes, dpi=300)
    pages_data = []
    
    for i, img in enumerate(images):
        custom_config = r'--oem 1 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config, lang='eng')
        
        cleaned_text = clean_ocr_text(text)
        
        pages_data.append({
            'page_num': i + 1,
            'text': cleaned_text,
            'image': img
        })
    
    return pages_data

def convert_image_to_rgb(img):
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3])
        return rgb_img
    elif img.mode != 'RGB':
        return img.convert('RGB')
    return img

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
        img_bytes_list = []
        
        for img_file in image_list:
            try:
                img_file.seek(0)
                img = Image.open(img_file)
                
                img = convert_image_to_rgb(img)
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=95)
                img_buffer.seek(0)
                img_bytes_list.append(img_buffer.getvalue())
                
            except Exception as e:
                st.warning(f"Skipping image {img_file.name}: {str(e)}")
                continue
        
        if not img_bytes_list:
            raise ValueError("No valid images to convert")
        
        return bytes(img2pdf.convert(img_bytes_list))

    def extract_text(self, pdf_bytes):
        images = convert_from_bytes(pdf_bytes, dpi=300)
        full_text = ""
        for i, img in enumerate(images):
            custom_config = r'--oem 1 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config, lang='eng')
            cleaned_text = clean_ocr_text(text)
            full_text += cleaned_text + "\n\n"
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
                
                is_mobile = st.checkbox("Mobile View Mode", value=False)
                
                if is_mobile:
                    page_idx = st.number_input("Page", 1, len(pages), 1, key="page_mobile") - 1
                    current_img = pages[page_idx].copy()
                    
                    st.divider()
                    edit_mode = st.radio("Tool", ["Add Signature", "Add Text", "Whiteout"], key="tool_mobile")
                    
                    overlay_img = None
                    if edit_mode == "Add Signature":
                        sig_src = st.radio("Source", ["Pad", "File"], key="sig_src_mobile")
                        if sig_src == "Pad":
                            canv = st_canvas(fill_color="rgba(0,0,0,0)", stroke_width=2, stroke_color="#000", background_color="#fff", height=200, width=280, drawing_mode="freedraw", key="sig_mobile")
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
                            u = st.file_uploader("Upload PNG", type=['png'], key="sig_file_mobile")
                            if u: overlay_img = Image.open(u)
                    elif edit_mode == "Add Text":
                        txt = st.text_input("Text Content", "Enter Text", key="text_mobile")
                        t_sz = st.slider("Text Size", 10, 100, 24, key="text_size_mobile")
                        t_clr = st.color_picker("Color", "#000000", key="text_color_mobile")
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
                        x = st.slider("X Position", 0, current_img.width, 50, key="x_mobile")
                        y = st.slider("Y Position", 0, current_img.height, 50, key="y_mobile")
                        sc = st.slider("Scale", 0.1, 5.0, 1.0, key="scale_mobile")
                        nw, nh = int(overlay_img.width*sc), int(overlay_img.height*sc)
                        if nw > 0 and nh > 0: overlay_img = overlay_img.resize((nw, nh))
                    
                    st.subheader("Live Preview")
                    prev = current_img.convert("RGBA")
                    if overlay_img: prev.paste(overlay_img, (x, y), overlay_img)
                    st.image(prev, use_container_width=True)
                    
                    if st.button("Apply and Download", key="apply_mobile"):
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
                            st.download_button("Download Edited PDF", bytes(out.getvalue()), "edited.pdf", "application/pdf", key="download_mobile")
                
                else:
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
        st.write("Upload multiple images (up to 1000) and convert them to a single PDF file")
        
        files = st.file_uploader("Upload Images", accept_multiple_files=True, type=['jpg','png','jpeg','bmp','gif','tiff'], key="img_uploader")
        
        if files:
            num_files = len(files)
            
            if num_files > 1000:
                st.error(f"Too many files selected ({num_files}). Maximum allowed is 1000. Please select fewer images.")
            else:
                st.success(f"Selected {num_files} image(s)")
                
                cols = st.columns(min(num_files, 4))
                for idx, file in enumerate(files[:20]):
                    with cols[idx % 4]:
                        try:
                            img = Image.open(file)
                            st.image(img, caption=f"{idx+1}. {file.name}", use_container_width=True)
                            file.seek(0)
                        except:
                            st.warning(f"Cannot preview {file.name}")
                
                if num_files > 20:
                    st.info(f"Showing first 20 images. {num_files - 20} more images will be included in the PDF.")
                
                st.divider()
                
                if st.button("Convert to PDF", use_container_width=True):
                    with st.spinner(f"Converting {num_files} images to PDF..."):
                        try:
                            res = processor.images_to_pdf(files)
                            st.success("Conversion complete")
                            st.download_button("Download PDF", res, "converted.pdf", "application/pdf", use_container_width=True)
                        except Exception as e:
                            st.error(f"Error during conversion: {str(e)}")

    elif choice == "OCR Extract Text":
        st.header("Extract and Edit Text from PDF")
        st.write("Extract text using OCR, edit it, and download as TXT or PDF with proper formatting")
        
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            if st.button("Process PDF for OCR", use_container_width=True):
                with st.spinner("Extracting text from PDF..."):
                    pages_data = enhanced_ocr_extraction(f.read())
                    st.session_state['ocr_pages'] = pages_data

            if 'ocr_pages' in st.session_state:
                st.success(f"Extraction Complete - {len(st.session_state['ocr_pages'])} page(s) processed")
                
                st.subheader("Review and Edit Extracted Text")
                st.info("Edit the text below to fix any recognition errors. The alignment will be preserved when downloading as PDF.")
                
                edited_pages = []
                for page_data in st.session_state['ocr_pages']:
                    with st.expander(f"Page {page_data['page_num']}", expanded=True):
                        edited_text = st.text_area(
                            f"Edit Page {page_data['page_num']}", 
                            page_data['text'], 
                            height=400,
                            key=f"page_{page_data['page_num']}",
                            label_visibility="collapsed"
                        )
                        edited_pages.append(edited_text)
                
                final_text = "\n\n".join(edited_pages)
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("Download as TXT", final_text, "extracted.txt", "text/plain", use_container_width=True)
                with col2:
                    pdf_data = fast_text_to_pdf(final_text)
                    st.download_button("Download as PDF", pdf_data, "extracted.pdf", "application/pdf", use_container_width=True)

    elif choice == "Merge PDFs":
        st.header("Merge Multiple PDFs")
        st.write("Combine multiple PDF files into a single document")
        
        files = st.file_uploader("Upload PDF Files", accept_multiple_files=True, type=['pdf'])
        
        if files:
            st.success(f"Selected {len(files)} PDF file(s)")
            for idx, file in enumerate(files):
                st.write(f"{idx+1}. {file.name}")
            
            st.divider()
            
            if st.button("Merge PDFs", use_container_width=True):
                with st.spinner("Merging PDFs..."):
                    res = processor.merge_pdfs(files)
                    st.success("Merge complete")
                    st.download_button("Download Merged PDF", res, "merged.pdf", "application/pdf", use_container_width=True)

    elif choice == "Split and Crop":
        st.header("Crop PDF Pages")
        st.write("Select a page and crop specific areas")
        
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t:
                t.write(f.read()); t_n = t.name
            try:
                imgs = convert_from_bytes(open(t_n, 'rb').read())
                idx = st.number_input("Select Page", 1, len(imgs), 1) - 1
                st.info("Drag to select the area you want to crop")
                crp = st_cropper(imgs[idx], realtime_update=True, box_color='red', aspect_ratio=None)
                
                st.divider()
                
                if st.button("Save Cropped Area", use_container_width=True):
                    b = io.BytesIO(); crp.save(b, format='PNG')
                    st.success("Crop complete")
                    st.download_button("Download Cropped PDF", bytes(img2pdf.convert(b.getvalue())), "crop.pdf", "application/pdf", use_container_width=True)
            finally:
                cleanup_temp_file(t_n)

    elif choice == "Repair Broken PDF":
        st.header("Repair Corrupted PDF")
        st.write("Fix and repair damaged or corrupted PDF files")
        
        f = st.file_uploader("Upload PDF", type=['pdf'])
        if f:
            if st.button("Repair PDF", use_container_width=True):
                with st.spinner("Repairing PDF..."):
                    res = processor.repair_pdf(f)
                    st.success("PDF repaired successfully")
                    st.download_button("Download Repaired PDF", res, "repaired.pdf", "application/pdf", use_container_width=True)

    elif choice == "Convert PDF Format":
        st.header("Convert PDF to Other Formats")
        st.write("Convert PDF to images or text documents")
        
        f = st.file_uploader("Upload PDF", type=['pdf'])
        fmt = st.selectbox("Convert To", ["JPG Page 1", "Word Text"])
        
        if f:
            if st.button("Convert", use_container_width=True):
                with st.spinner("Converting..."):
                    if fmt == "JPG Page 1":
                        img = convert_from_bytes(f.read())[0]
                        b = io.BytesIO(); img.save(b, format="JPEG")
                        st.success("Conversion complete")
                        st.download_button("Download JPG", bytes(b.getvalue()), "page1.jpg", use_container_width=True)
                    else:
                        txt = processor.extract_text(f.read())
                        st.success("Conversion complete")
                        st.download_button("Download Text", txt, "export.doc", use_container_width=True)

if __name__ == "__main__":
    main()
