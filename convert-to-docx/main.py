from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from tempfile import NamedTemporaryFile
import re
from typing import List, Dict, Any
import io

app = FastAPI()

def set_doc_style(doc):
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

def add_bullet_points(doc, items):
    for item in items:
        p = doc.add_paragraph(item, style='List Bullet')
        p.paragraph_format.space_after = Pt(6)

def add_numbered_points(doc, items):
    for item in items:
        p = doc.add_paragraph(item, style='List Number')
        p.paragraph_format.space_after = Pt(6)

def parse_docx_to_json(doc):
    """Parse a DOCX document back to the original JSON structure"""
    result = {
        "title": "",
        "introduction": {
            "hook": "",
            "theme": "",
            "preview": ""
        },
        "fact_section": {
            "organization": "",
            "key_facts_to_emphasize": [],
            "bad_facts_to_address": [],
            "fact_themes": []
        },
        "arguments": [],
        "conclusion": {
            "specific_relief": [],
            "final_theme": ""
        },
        "style_notes": []
    }
    
    current_section = None
    current_argument = None
    current_subsection = None
    collecting_bullets = False
    bullet_collector = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Check if it's a heading
        style_name = para.style.name
        is_heading = 'Heading' in style_name
        is_bullet = para.style.name == 'List Bullet' or para.style.name == 'List Number'
        
        # Title (centered, bold, no heading style)
        if para.alignment == WD_ALIGN_PARAGRAPH.CENTER and para.runs and para.runs[0].bold:
            result["title"] = text
            continue
            
        # Main headings
        if is_heading and 'Heading 1' in style_name:
            # Save any pending bullets
            if collecting_bullets and bullet_collector:
                _save_bullets(result, current_section, current_subsection, bullet_collector, current_argument)
                bullet_collector = []
                collecting_bullets = False
                
            if text == "Introduction":
                current_section = "introduction"
                current_argument = None
            elif text == "Statement of Facts":
                current_section = "fact_section"
                current_argument = None
            elif text == "Conclusion":
                current_section = "conclusion"
                current_argument = None
            elif text == "Style Notes":
                current_section = "style_notes"
                current_argument = None
            continue
            
        # Argument headings (Heading 2)
        if is_heading and 'Heading 2' in style_name and current_section not in ["introduction", "fact_section", "conclusion", "style_notes"]:
            # Save any pending bullets
            if collecting_bullets and bullet_collector:
                _save_bullets(result, current_section, current_subsection, bullet_collector, current_argument)
                bullet_collector = []
                collecting_bullets = False
                
            current_argument = {
                "heading": text,
                "summary": "",
                "structure": [],
                "key_authorities": [],
                "fact_integration": [],
                "counter_argument_response": []
            }
            result["arguments"].append(current_argument)
            current_section = "arguments"
            continue
            
        # Handle bullet points
        if is_bullet:
            bullet_collector.append(text)
            collecting_bullets = True
            continue
            
        # If we hit a non-bullet after collecting bullets, save them
        if collecting_bullets and bullet_collector:
            _save_bullets(result, current_section, current_subsection, bullet_collector, current_argument)
            bullet_collector = []
            collecting_bullets = False
            
        # Parse field values
        if text.startswith("Hook:"):
            result["introduction"]["hook"] = text[5:].strip()
        elif text.startswith("Theme:"):
            result["introduction"]["theme"] = text[6:].strip()
        elif text.startswith("Preview:"):
            result["introduction"]["preview"] = text[8:].strip()
        elif text.startswith("Organization:"):
            result["fact_section"]["organization"] = text[13:].strip()
        elif text.startswith("Summary:") and current_argument:
            current_argument["summary"] = text[8:].strip()
        elif text.startswith("Final Theme:"):
            result["conclusion"]["final_theme"] = text[12:].strip()
        elif text == "Key Facts to Emphasize:":
            current_subsection = "key_facts_to_emphasize"
        elif text == "Bad Facts to Address:":
            current_subsection = "bad_facts_to_address"
        elif text == "Fact Themes:":
            current_subsection = "fact_themes"
        elif text == "Structure:":
            current_subsection = "structure"
        elif text == "Key Authorities:":
            current_subsection = "key_authorities"
        elif text == "Fact Integration:":
            current_subsection = "fact_integration"
        elif text == "Counter-Argument Response:":
            current_subsection = "counter_argument_response"
            
    # Save any remaining bullets
    if collecting_bullets and bullet_collector:
        _save_bullets(result, current_section, current_subsection, bullet_collector, current_argument)
        
    return result

def _save_bullets(result, section, subsection, bullets, current_argument):
    """Helper function to save collected bullet points to the appropriate section"""
    if section == "fact_section" and subsection:
        result["fact_section"][subsection] = bullets.copy()
    elif section == "arguments" and current_argument and subsection:
        if subsection in ["structure"]:
            current_argument[subsection] = bullets.copy()
        elif subsection == "key_authorities":
            # Try to parse complex authority format
            for bullet in bullets:
                parsed = _parse_authority(bullet)
                current_argument["key_authorities"].append(parsed)
        elif subsection == "fact_integration":
            # Try to parse fact integration format
            for bullet in bullets:
                parsed = _parse_fact_integration(bullet)
                current_argument["fact_integration"].append(parsed)
        elif subsection == "counter_argument_response":
            # Try to parse counter-argument format
            for bullet in bullets:
                parsed = _parse_counter_argument(bullet)
                current_argument["counter_argument_response"].append(parsed)
    elif section == "conclusion" and subsection == "specific_relief":
        result["conclusion"]["specific_relief"] = bullets.copy()
    elif section == "style_notes":
        result["style_notes"] = bullets.copy()

def _parse_authority(text):
    """Parse key authority text back to structured format"""
    # Try to match pattern: "Case Name – Citation: Principle (Why it matters)"
    pattern = r'^(.+?)\s*–\s*(.+?):\s*(.+?)\s*\((.+?)\)$'
    match = re.match(pattern, text)
    
    if match:
        return {
            "case_name": match.group(1).strip(),
            "citation": match.group(2).strip(),
            "principle": match.group(3).strip(),
            "why_it_matters": match.group(4).strip()
        }
    else:
        # Return as simple string if pattern doesn't match
        return text

def _parse_fact_integration(text):
    """Parse fact integration text back to structured format"""
    # Try to match pattern: "Fact – Relevance"
    pattern = r'^(.+?)\s*–\s*(.+)$'
    match = re.match(pattern, text)
    
    if match:
        return {
            "fact": match.group(1).strip(),
            "relevance": match.group(2).strip()
        }
    else:
        return text

def _parse_counter_argument(text):
    """Parse counter-argument text back to structured format"""
    # Try to match pattern: "Opposing argument → Response (Strategic value)"
    pattern = r'^(.+?)\s*→\s*(.+?)\s*\((.+?)\)$'
    match = re.match(pattern, text)
    
    if match:
        return {
            "opposing_argument": match.group(1).strip(),
            "response": match.group(2).strip(),
            "strategic_value": match.group(3).strip()
        }
    else:
        return text

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/generate-outline/")
async def generate_outline(request: Request):
    data = await request.json()
    doc = Document()
    set_doc_style(doc)

    title = doc.add_paragraph(data['title'])
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True

    doc.add_heading("Introduction", level=1)
    doc.add_paragraph(f"Hook: {data['introduction']['hook']}")
    doc.add_paragraph(f"Theme: {data['introduction']['theme']}")
    doc.add_paragraph(f"Preview: {data['introduction']['preview']}")

    doc.add_heading("Statement of Facts", level=1)
    doc.add_paragraph(f"Organization: {data['fact_section']['organization']}")

    doc.add_paragraph("Key Facts to Emphasize:")
    add_bullet_points(doc, data['fact_section']['key_facts_to_emphasize'])

    doc.add_paragraph("Bad Facts to Address:")
    add_bullet_points(doc, data['fact_section']['bad_facts_to_address'])

    doc.add_paragraph("Fact Themes:")
    add_bullet_points(doc, data['fact_section']['fact_themes'])

    for arg in data['arguments']:
        doc.add_heading(arg['heading'], level=2)
        doc.add_paragraph(f"Summary: {arg['summary']}")

        doc.add_paragraph("Structure:")
        add_bullet_points(doc, arg['structure'])

        doc.add_paragraph("Key Authorities:")
        for auth in arg['key_authorities']:
            if isinstance(auth, str):
                doc.add_paragraph(auth, style='List Bullet')
            else:
                summary = f"{auth['case_name']} – {auth['citation']}: {auth['principle']} ({auth['why_it_matters']})"
                doc.add_paragraph(summary, style='List Bullet')

        doc.add_paragraph("Fact Integration:")
        for fact in arg['fact_integration']:
            if isinstance(fact, str):
                doc.add_paragraph(fact, style='List Bullet')
            else:
                summary = f"{fact['fact']} – {fact['relevance']}"
                doc.add_paragraph(summary, style='List Bullet')

        doc.add_paragraph("Counter-Argument Response:")
        for reply in arg['counter_argument_response']:
            if isinstance(reply, str):
                doc.add_paragraph(reply, style='List Bullet')
            else:
                summary = f"{reply['opposing_argument']} → {reply['response']} ({reply['strategic_value']})"
                doc.add_paragraph(summary, style='List Bullet')

    doc.add_heading("Conclusion", level=1)
    add_bullet_points(doc, data['conclusion']['specific_relief'])
    doc.add_paragraph(f"Final Theme: {data['conclusion']['final_theme']}")

    doc.add_heading("Style Notes", level=1)
    add_bullet_points(doc, data['style_notes'])

    tmp = NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp.name)
    return FileResponse(tmp.name, filename="Legal_Outline.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.post("/parse-outline/")
async def parse_outline(file: UploadFile = File(...)):
    """Parse an uploaded DOCX file back to JSON structure"""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="File must be a .docx document")
    
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Load the document
        doc = Document(io.BytesIO(contents))
        
        # Parse the document
        parsed_data = parse_docx_to_json(doc)
        
        return JSONResponse(content=parsed_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing document: {str(e)}")