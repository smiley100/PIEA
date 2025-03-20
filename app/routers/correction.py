from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.services.correction_service import (
    extract_text_from_uploaded_file,
    generate_correction,
    create_pdf_from_text,
    generate_correction_report
)
from io import BytesIO

router = APIRouter(prefix="/api/v1", tags=["correction"])

@router.post("/generate-correction")
async def generate_correction_endpoint(file: UploadFile = File(...)):
    try:
        # Extraire le texte du PDF en flux
        text = await extract_text_from_uploaded_file(file)

        # Générer le corrigé en utilisant Ollama
        correction = await generate_correction(text)

        # Créer un PDF à partir du corrigé
        pdf_bytes = create_pdf_from_text(correction)
        pdf_stream = BytesIO(pdf_bytes)

        # Retourner le PDF en flux au client
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=correction.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate_devoir(
    devoir: UploadFile = File(...), 
    correction: UploadFile = File(...)
):
    try:
        # Extraire les textes des fichiers PDF
        devoir_text = await extract_text_from_uploaded_file(devoir)
        correction_text = await extract_text_from_uploaded_file(correction)

        # Générer le rapport de correction
        correction_report = await generate_correction_report(devoir_text, correction_text)

        # Générer le PDF de correction
        pdf_bytes = create_pdf_from_text(correction_report)
        pdf_stream = BytesIO(pdf_bytes)

        # Retourner le PDF généré
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=correction_report.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))