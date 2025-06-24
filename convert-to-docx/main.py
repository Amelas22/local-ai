from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
from tempfile import NamedTemporaryFile
import uvicorn

app = FastAPI()

def add_bullet_points(doc, items):
    for item in items:
        doc.add_paragraph(item, style='List Bullet')

def add_numbered_points(doc, items):
    for item in items:
        doc.add_paragraph(item, style='List Number')

@app.post("/generate-outline/")
async def generate_outline(request: Request):
    data = await request.json()
    doc = Document()

    doc.add_heading(data['title'], 0)

    # Introduction
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph(f"Hook: {data['introduction']['hook']}")
    doc.add_paragraph(f"Theme: {data['introduction']['theme']}")
    doc.add_paragraph(f"Preview: {data['introduction']['preview']}")

    # Fact Section
    doc.add_heading("Fact Section", level=1)
    doc.add_paragraph(f"Organization: {data['fact_section']['organization']}")

    doc.add_paragraph("Key Facts to Emphasize:")
    add_bullet_points(doc, data['fact_section']['key_facts_to_emphasize'])

    doc.add_paragraph("Bad Facts to Address:")
    add_bullet_points(doc, data['fact_section']['bad_facts_to_address'])

    doc.add_paragraph("Fact Themes:")
    add_bullet_points(doc, data['fact_section']['fact_themes'])

    # Arguments
    for arg in data['arguments']:
        doc.add_heading(arg['heading'], level=2)
        doc.add_paragraph(f"Summary: {arg['summary']}")

        doc.add_paragraph("Structure:")
        add_numbered_points(doc, arg['structure'])

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

    # Conclusion
    doc.add_heading("Conclusion", level=1)
    add_bullet_points(doc, data['conclusion']['specific_relief'])
    doc.add_paragraph(f"Final Theme: {data['conclusion']['final_theme']}")

    # Style Notes
    doc.add_heading("Style Notes", level=1)
    add_bullet_points(doc, data['style_notes'])

    tmp = NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp.name)
    return FileResponse(tmp.name, filename="Legal_Outline.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
