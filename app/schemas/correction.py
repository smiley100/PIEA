from pydantic import BaseModel

class CorrectionRequest(BaseModel):
    pdf_path: str  # Optionnel, si vous utilisez des chemins de fichiers

class CorrectionResponse(BaseModel):
    correction_path: str  # Optionnel, si vous retournez un chemin de fichier