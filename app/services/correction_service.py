from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import ollama
import textwrap
import re



async def extract_text_from_uploaded_file(file) -> str:
    """Extrait le texte d'un fichier PDF uploadé en le traitant en flux."""
    reader = PdfReader(file.file)  # Utilise le fichier uploadé comme flux
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


async def generate_correction(text: str) -> str:
    """Génère un corrigé en utilisant Ollama."""
    prompt = f"""
Tu es un professeur expert en bases de données et en correction d'examens.
Réponds aux questions du devoir ci-dessus:

{text}
"""

    # Demande de correction à Ollama
    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Récupération de la réponse
    corrected_text = response["message"]["content"]

    # Après avoir obtenu la réponse, nettoyage des éléments indésirables
    # Supprimer ce qui est entre <think> et </think>
    cleaned_text = re.sub(r"<think>.*?</think>", "", corrected_text)

    # Supprimer exactement "###", "#####", "```sql", "**" et "---"
    cleaned_text = re.sub(r"###", "", cleaned_text)  # Supprime les "###"
    cleaned_text = re.sub(r"#####", "", cleaned_text)  # Supprime les "#####"
    cleaned_text = re.sub(r"```sql", "", cleaned_text)  # Supprime "```sql"
    cleaned_text = re.sub(r"\*\*", "", cleaned_text)  # Supprime les "**"
    cleaned_text = re.sub(r"---", "", cleaned_text)  # Supprime les "---"

    return cleaned_text




def create_pdf_from_text(text: str) -> bytes:
    """Crée un PDF avec des marges réduites et un meilleur formatage."""
    pdf_bytes = BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=letter)
    c.setFont("Helvetica", 12)

    # Ajustement des marges et de la largeur du texte
    margin_x = 30  # Marge horizontale réduite
    margin_y_top = 750  # Position de départ en haut
    margin_y_bottom = 50  # Position limite en bas
    line_height = 16  # Espacement entre les lignes

    y = margin_y_top

    for paragraph in text.split("\n"):
        wrapped_lines = textwrap.wrap(paragraph, width=80)  # Augmente la largeur du texte

        for line in wrapped_lines:
            c.drawString(margin_x, y, line)
            y -= line_height  # Déplacer vers le bas

            if y < margin_y_bottom:  # Si on atteint le bas, on crée une nouvelle page
                c.showPage()
                c.setFont("Helvetica", 12)
                y = margin_y_top  # Recommencer en haut

    c.save()
    pdf_bytes.seek(0)
    return pdf_bytes.getvalue()


async def generate_correction_report(devoir_text: str, correction_text: str) -> str:
    """Compare le devoir de l'étudiant avec la correction du professeur et génère une note et justification."""
    prompt = f"""
    Tu es un professeur de bases de données. Ta tâche est de corriger le devoir de l'étudiant en le comparant à la correction officielle.
    
    ### Consignes :
    - **Attribue une note sur 20 en fonction du barème** (si un barème est donné dans la correction, utilise-le. Sinon, crée-en un adapté).
    - **Justifie chaque point retiré** en expliquant les erreurs.
    - **Ne rends que la note finale et un feedback détaillé sans balises Markdown.**
    
    ---  
    **Devoir de l'étudiant :**  
    {devoir_text}

    ---  
    **Correction du professeur :**  
    {correction_text}
    """
    
    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[{"role": "user", "content": prompt}]
    )

    corrected_text = response["message"]["content"]

    # Nettoyage des balises non souhaitées
    cleaned_text = re.sub(r"<.*?>", "", corrected_text)  # Supprime les balises HTML/XML
    cleaned_text = re.sub(r"###|#####|```sql|```|\*\*|---", "", cleaned_text)  # Supprime les caractères spécifiés
    return cleaned_text.strip()
