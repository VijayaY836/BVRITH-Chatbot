"""Extract images from the .docx knowledge base and map them to sections."""
import os
from pathlib import Path
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree

ROOT = Path(__file__).resolve().parent
DOCX_PATH = ROOT / "BVRITH_Comprehensive_Knowledge_Base.docx"
IMAGES_DIR = ROOT / "images"

# Map image rId to section heading based on paragraph context
SECTION_IMAGE_MAP = {
    # These will be populated by analyzing the document
}

def extract_images():
    """Extract all images from the docx and map them to sections."""
    doc = Document(str(DOCX_PATH))
    IMAGES_DIR.mkdir(exist_ok=True)
    
    # Extract image files from the docx zip
    import zipfile
    with zipfile.ZipFile(str(DOCX_PATH), 'r') as z:
        image_files = [f for f in z.namelist() if f.startswith('word/media/')]
        print(f"Found {len(image_files)} image files in docx")
        
        for img_file in image_files:
            # Extract to images directory
            img_name = os.path.basename(img_file)
            img_path = IMAGES_DIR / img_name
            with z.open(img_file) as source:
                with open(img_path, 'wb') as target:
                    target.write(source.read())
            print(f"  Extracted: {img_name}")
    
    # Map images to sections by finding which paragraph contains each image
    nsmap = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    }
    
    image_section_map = {}
    current_section = "Intro"
    
    for para in doc.paragraphs:
        text = para.text.strip()
        
        # Detect section headings
        import re
        m = re.match(r'^(\d+)\.\s+(.+)$', text)
        if m:
            current_section = m.group(2).strip()
        
        # Check for images in this paragraph
        drawings = para._element.findall('.//w:drawing', nsmap)
        for drawing in drawings:
            # Find the relationship ID
            blip = drawing.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
            for b in blip:
                embed = b.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if embed:
                    # Get the image file name from the relationship
                    rel = doc.part.rels[embed]
                    if rel:
                        img_name = os.path.basename(rel.target_ref)
                        image_section_map[img_name] = current_section
                        print(f"  Image '{img_name}' -> Section: '{current_section}'")
    
    return image_section_map

if __name__ == "__main__":
    image_map = extract_images()
    print(f"\nTotal images mapped: {len(image_map)}")
    
    # Write the mapping to a JSON file for use by app.py
    import json
    with open(ROOT / "image_section_map.json", "w") as f:
        json.dump(image_map, f, indent=2)
    print("Image section map written to image_section_map.json")