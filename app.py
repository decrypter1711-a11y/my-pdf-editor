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
    .stSlider > div [data-baseweb="slider"] { margin-bottom: 20px; }
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
if "ocr_result_pdf" not in st.session_state:
    st.session_state.ocr_result_pdf = None
if "ocr_text_preview" not in st.session_state:
    st.session_state.ocr_text_preview = ""

def purge_temporary_resource(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

class CoreEngine:
    def __init__(self):
        self.io_stream = io.BytesIO()

    def consolidate_pdf_entities(self, sequence):
        aggregate = PdfWriter()
        for item in sequence:
            item.seek(0)
            aggregate.append(item)
        aggregate.write(self.memory_buffer)
        return bytes(self.memory_buffer.getvalue())

    def raster_to_vector_pdf(self, image_sequence):
        payload = []
        for frame in image_sequence:
            frame.seek(0)
            payload.append(frame.read())
        return bytes(img2pdf.convert(payload, rotation=img2pdf.Rotation.ifvalid))

    def linguistic_extraction(self, stream):
        visual_nodes = convert_from_bytes(stream)
        transcription = ""
        for index, node in enumerate(visual_nodes):
            segment = pytesseract.image_to_string(node, config='--psm 3')
            segment = re.sub(r'^\s*[e|c|o]\s+', '• ', segment, flags=re.MULTILINE)
            segment = re.sub(r'^\s*[\-_]\s+', '• ', segment, flags=re.MULTILINE)
            transcription += f"{segment}\n"
        return transcription

    def generate_searchable_hocr(self, stream):
        visual_nodes = convert_from_bytes(stream)
        constructor = PdfWriter()
        for node in visual_nodes:
            hocr_layer = pytesseract.image_to_pdf_or_hocr(node, extension='pdf', config='--psm 3')
            node_reader = PdfReader(io.BytesIO(hocr_layer))
            constructor.add_page(node_reader.pages[0])
        buffer = io.BytesIO()
        constructor.write(buffer)
        return bytes(buffer.getvalue())

    def structural_restoration(self, stream_obj):
        stream_obj.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as proxy:
            proxy.write(stream_obj.read())
            proxy_path = proxy.name
        try:
            foundation = pikepdf.open(proxy_path, allow_overwriting_input=True)
            output = io.BytesIO()
            foundation.save(output)
            return bytes(output.getvalue())
        finally:
            purge_temporary_resource(proxy_path)

def main_orchestrator():
    st.sidebar.header("PDF Studio Controller")
    navigation = [
        "Visual Editor", 
        "Image to PDF", 
        "OCR Extract Text", 
        "Merge PDFs", 
        "Split and Crop", 
        "Repair Broken PDF", 
        "Convert PDF Format"
    ]
    interaction_mode = st.sidebar.radio("Executive Modules", navigation)
    processor = CoreEngine()

    if interaction_mode == "Visual Editor":
        st.header("Visual Manipulation Layer")
        uplink = st.file_uploader("Source PDF Transaction", type=['pdf'], key="global_viz_uplink")
        
        if uplink:
            stream_identity = uplink.name + str(uplink.size)
            if st.session_state.active_file_hash != stream_identity:
                st.session_state.edited_pdf_bytes = None
                st.session_state.active_file_hash = stream_identity

        if uplink:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as session_buffer:
                session_buffer.write(uplink.getvalue())
                session_path = session_buffer.name
            try:
                frame_collection = convert_from_bytes(open(session_path, 'rb').read())
                layout_a, layout_b = st.columns([1, 2])
                
                with layout_a:
                    target_frame_index = st.number_input("Frame Selection", 1, len(frame_collection), 1) - 1
                    active_visual = frame_collection[target_frame_index].copy()
                    st.divider()
                    modality = st.radio("Modification Protocol", ["Add Signature", "Add Text", "Whiteout"])
                    sub_layer = None
                    
                    if modality == "Add Signature":
                        input_method = st.radio("Input Vector", ["Pad", "File"])
                        if input_method == "Pad":
                            canvas_registry = st_canvas(
                                fill_color="rgba(0,0,0,0)", 
                                stroke_width=2, 
                                stroke_color="#000", 
                                background_color="#fff", 
                                height=150, 
                                width=300, 
                                drawing_mode="freedraw", 
                                key="viz_canvas"
                            )
                            if canvas_registry.image_data is not None:
                                sub_layer = Image.fromarray(canvas_registry.image_data.astype('uint8'), 'RGBA')
                                pixel_map = sub_layer.getdata()
                                optimized_pixels = []
                                for pixel in pixel_map:
                                    if pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200: 
                                        optimized_pixels.append((255,255,255,0))
                                    else: 
                                        optimized_pixels.append(pixel)
                                sub_layer.putdata(optimized_pixels)
                                boundaries = sub_layer.getbbox()
                                if boundaries: 
                                    sub_layer = sub_layer.crop(boundaries)
                        else:
                            import_node = st.file_uploader("Alpha Channel PNG", type=['png'])
                            if import_node: 
                                sub_layer = Image.open(import_node).convert("RGBA")
                            
                    elif modality == "Add Text":
                        content_string = st.text_input("Literal Content", "Standardized Text")
                        font_magnitude = st.slider("Magnitude", 10, 200, 30)
                        chroma_value = st.color_picker("Hexadecimal Chroma", "#000000")
                        if content_string:
                            try:
                                typography = ImageFont.truetype("DejaVuSans.ttf", font_magnitude)
                            except:
                                typography = ImageFont.load_default()
                            metric_proxy = Image.new('RGBA', (1, 1))
                            draw_proxy = ImageDraw.Draw(metric_proxy)
                            glyph_box = draw_proxy.textbbox((0, 0), content_string, font=typography)
                            box_w, box_h = glyph_box[2] - glyph_box[0], glyph_box[3] - glyph_box[1]
                            sub_layer = Image.new('RGBA', (box_w + 20, box_h + 20), (255, 255, 255, 0))
                            rendering_context = ImageDraw.Draw(sub_layer)
                            rendering_context.text((10, 10), content_string, font=typography, fill=chroma_value)
                            
                    elif modality == "Whiteout":
                        sub_layer = Image.new('RGBA', (150, 75), (255,255,255,255))
                        
                    st.divider()
                    if sub_layer:
                        coord_x = st.slider("Horizontal Offset", 0, active_visual.width, 100)
                        coord_y = st.slider("Vertical Offset", 0, active_visual.height, 100)
                        dimension_scalar = st.slider("Geometric Scale", 0.05, 5.0, 1.0)
                        final_w, final_h = int(sub_layer.width*dimension_scalar), int(sub_layer.height*dimension_scalar)
                        if final_w > 0 and final_h > 0: 
                            sub_layer = sub_layer.resize((final_w, final_h), resample=Image.LANCZOS)
                        
                with layout_b:
                    st.subheader("Real-time Rendering Preview")
                    composition_base = active_visual.convert("RGBA")
                    if sub_layer:
                        composition_base.paste(sub_layer, (coord_x, coord_y), sub_layer)
                    st.image(composition_base, use_container_width=True)
                    
                    if st.button("Execute Injection Protocol"):
                        if sub_layer:
                            origin_reader = PdfReader(session_path)
                            output_constructor = PdfWriter()
                            
                            target_metadata = origin_reader.pages[target_frame_index]
                            media_w = float(target_metadata.mediabox.width)
                            media_h = float(target_metadata.mediabox.height)
                            
                            ratio_w, ratio_h = media_w/active_visual.width, media_h/active_visual.height
                            mapped_x = coord_x * ratio_w
                            mapped_y = (active_visual.height - coord_y - sub_layer.height) * ratio_h
                            mapped_w = sub_layer.width * ratio_w
                            mapped_h = sub_layer.height * ratio_h
                            
                            composite_io = io.BytesIO()
                            rendering_surface = canvas.Canvas(composite_io, pagesize=(media_w, media_h))
                            
                            if modality == "Whiteout":
                                rendering_surface.setFillColor(white)
                                rendering_surface.setStrokeColor(white)
                                rendering_surface.rect(mapped_x, mapped_y, mapped_w, mapped_h, fill=1, stroke=1)
                            elif modality == "Add Text":
                                rendering_surface.setFillColor(chroma_value)
                                rendering_surface.setFont("Helvetica", font_magnitude * ratio_h)
                                rendering_surface.drawString(mapped_x, mapped_y + (mapped_h/4), content_string)
                            else:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as asset_proxy:
                                    sub_layer.save(asset_proxy, format="PNG")
                                    asset_path = asset_proxy.name
                                rendering_surface.drawImage(asset_path, mapped_x, mapped_y, width=mapped_w, height=mapped_h, mask='auto')
                                purge_temporary_resource(asset_path)
                                
                            rendering_surface.save()
                            composite_io.seek(0)
                            overlay_node = PdfReader(composite_io)
                            
                            for idx, page_node in enumerate(origin_reader.pages):
                                if idx == target_frame_index:
                                    page_node.merge_page(overlay_node.pages[0])
                                output_constructor.add_page(page_node)
                                
                            final_binary_stream = io.BytesIO()
                            output_constructor.write(final_binary_stream)
                            st.session_state.edited_pdf_bytes = final_binary_stream.getvalue()
                            st.success("Delta Injection Synchronized")
                            
                    if st.session_state.edited_pdf_bytes is not None:
                        st.download_button(
                            label="Export Modified PDF Artifact", 
                            data=st.session_state.edited_pdf_bytes, 
                            file_name="modified_output.pdf", 
                            mime="application/pdf"
                        )
            finally:
                purge_temporary_resource(session_path)

    elif interaction_mode == "Image to PDF":
        st.header("Image Encapsulation Unit")
        asset_collection = st.file_uploader("Visual Assets", accept_multiple_files=True, type=['jpg','png','jpeg'])
        if asset_collection and st.button("Generate Encapsulation"):
            try:
                encapsulated_data = processor.raster_to_vector_pdf(asset_collection)
                st.download_button("Export PDF Entity", encapsulated_data, "collection_archive.pdf")
            except Exception as system_error:
                st.error(f"Encapsulation Failure: {system_error}")

    elif interaction_mode == "OCR Extract Text":
        st.header("Optical Character Recognition Core")
        scanned_input = st.file_uploader("Analog PDF Stream", type=['pdf'])
        if scanned_input:
            if st.button("Initiate Neural Scan"):
                with st.spinner("Processing Signal..."):
                    binary_payload = scanned_input.read()
                    st.session_state.ocr_text_preview = processor.linguistic_extraction(binary_payload)
                    st.session_state.ocr_result_pdf = processor.generate_searchable_hocr(binary_payload)
            
            if st.session_state.ocr_text_preview:
                st.text_area("Linguistic Buffer", st.session_state.ocr_text_preview, height=350)
                btn_layout_a, btn_layout_b = st.columns(2)
                with btn_layout_a:
                    st.download_button("Export Literal TXT", st.session_state.ocr_text_preview, "linguistic_data.txt")
                with btn_layout_b:
                    if st.session_state.ocr_result_pdf:
                        st.download_button("Export Hybrid Searchable PDF", st.session_state.ocr_result_pdf, "searchable_intel.pdf")

    elif interaction_mode == "Merge PDFs":
        st.header("Binary Stream Consolidation")
        fragment_list = st.file_uploader("PDF Fragments", accept_multiple_files=True, type=['pdf'])
        if fragment_list and st.button("Execute Consolidation"):
            try:
                consolidated_stream = processor.consolidate_pdf_entities(fragment_list)
                st.download_button("Export Consolidated Stream", consolidated_stream, "unified_system_data.pdf")
            except Exception as system_error:
                st.error(f"Consolidation Error: {system_error}")

    elif interaction_mode == "Split and Crop":
        st.header("Spatial Partitioning Engine")
        source_input = st.file_uploader("Geometry PDF", type=['pdf'])
        if source_input:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as partition_buffer:
                partition_buffer.write(source_input.read())
                partition_path = partition_buffer.name
            try:
                raster_set = convert_from_bytes(open(partition_path, 'rb').read())
                raster_index = st.number_input("Node Index", 1, len(raster_set), 1) - 1
                spatial_selector = st_cropper(raster_set[raster_index], realtime_update=True, box_color='blue')
                if st.button("Commit Partition"):
                    raster_stream = io.BytesIO()
                    spatial_selector.save(raster_stream, format='PNG')
                    st.download_button("Export Partition PDF", bytes(img2pdf.convert(raster_stream.getvalue())), "spatial_partition.pdf")
            finally:
                purge_temporary_resource(partition_path)

    elif interaction_mode == "Repair Broken PDF":
        st.header("Structural Integrity Restoration")
        corrupted_input = st.file_uploader("Damaged Binary Object", type=['pdf'])
        if corrupted_input and st.button("Initiate Restoration"):
            try:
                restored_entity = processor.structural_restoration(corrupted_input)
                st.download_button("Export Restored Entity", restored_entity, "restored_system_data.pdf")
            except Exception as system_error:
                st.error(f"Restoration Critical Failure: {system_error}")

    elif interaction_mode == "Convert PDF Format":
        st.header("Polymorphic Format Conversion")
        conversion_source = st.file_uploader("Origin PDF", type=['pdf'])
        target_schema = st.selectbox("Destination Schema", ["JPG Raster Page 1", "Word Processor Text"])
        if conversion_source and st.button("Commence Polymorphism"):
            if "JPG" in target_schema:
                raster_layer = convert_from_bytes(conversion_source.read())[0]
                image_stream = io.BytesIO()
                raster_layer.save(image_stream, format="JPEG")
                st.download_button("Export Raster JPG", bytes(image_stream.getvalue()), "rasterized_page.jpg")
            else:
                literal_data = processor.linguistic_extraction(conversion_source.read())
                st.download_button("Export Document Object", literal_data, "polymorphic_export.doc")

    st.markdown("---")
    st.markdown("### ENTERPRISE ARCHITECTURE PDF ECOSYSTEM")
    st.caption("ZERO-TRUST DATA PROCESSING | CLIENT-SIDE RAM VOLATILITY | HARDENED PDF MANIPULATION")

if __name__ == "__main__":
    main_orchestrator()
