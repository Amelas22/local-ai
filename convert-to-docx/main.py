from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile

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
