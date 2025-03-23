from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import ollama
import textwrap
import re
import os
import chardet




async def extract_text_from_uploaded_file(file) -> str:
    """
    Extrait le texte d'un fichier uploadé en le traitant en flux.
    Args:
        file (Any):Le fichier uploade
    Returns:
        str: Texte extrait du fichier
    """

    if not file.filename:
        return "Nom de fichier inconnu."
    
    _, extension = os.path.splitext(file.filename)
    
    try:
        if extension.lower() == ".pdf":
            return await extract_from_pdf(file)
        elif extension.lower() == ".latex":
            return await extract_from_latex(file)
        else:  # texte ou autre format texte
            return await extract_from_text(file)
    except Exception as e:
        return (f"Erreur lors de l'extraction du fichier ({extension}): {e}")

async def extract_from_pdf(file) -> str:
    """
    Extrait le texte d'un fichier PDF avec des optimisations pour les formats d'évaluation.
    Args:
        file (Any):Le fichier uploade
    Returns:
        str: Texte extrait du fichier pdf
    """
    try:
        reader = PdfReader(file.file)  # Utilise le fichier uploadé comme flux
        text = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                # Préservation des numéros de questions et de leur formatting
                content = re.sub(r'(\d+[\)\.-]\s)', r'\n\1', content)
                # Préservation des questions à points (n pts)
                content = re.sub(r'\((\d+)\s?(?:point|pt)s?\)', r'(\1 pts)', content, flags=re.IGNORECASE)
                text.append(content)
            
        full_text = "\n".join(text)
          
        # Nettoyage final pour les questions d'évaluation
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Limit blank lines
            
        return full_text
    except Exception as e:
        return (f"Erreur spécifique à l'extraction PDF: {e}")


async def extract_from_latex(file) -> str:
    """
    Extrait le texte d'un fichier LaTeX en préservant la structure des questions.
    Args:
        file (Any):Le fichier uploade
    Returns:
        str: Texte extrait du fichier pdf
    """
    try:
        raw_data = await file.read()
    
        # Détection de l'encodage
        result = chardet.detect(raw_data)
        encoding = result['encoding'] if result['confidence'] > 0.7 else 'utf-8'

        # Décoder le contenu avec l'encodage détecté
        content = raw_data.decode(encoding, errors='replace')

        # Préserver les environnements de questions/exercices
        content = re.sub(r'\\begin\{(question|exercise|exercice|document|questions)\}', r'\n\n', content, flags=re.IGNORECASE)
        content = re.sub(r'\\end\{(question|exercise|exercice|document|questions)\}', r'\n\n', content, flags=re.IGNORECASE)
        
        # Préserver les numéros de questions
        content = re.sub(r'\\item', r'\n', content)
        
        # Supprimer les commentaires
        content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
        
        # Supprimer les commandes LaTeX courantes mais préserver le texte
        content = re.sub(r'\\(section|subsection|paragraph)\{(.*?)\}', r'\n\n\2\n', content)
        content = re.sub(r'\\[a-zA-Z]+(\[.*?\])?(?=\{)', '', content)
        content = re.sub(r'\{|\}', '', content)
        
        # Nettoyer les espaces excessifs tout en préservant la structure
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    except Exception as e:
        return f"Erreur spécifique à l'extraction LaTeX: {e}"


async def extract_from_text(file) -> str:
    """
    Extrait le texte d'un fichier texte avec détection d'encodage, en prenant en compte un fichier uploadé via un POST.
    Args:
        file (Any):Le fichier uploade
    Returns:
        str: Texte extrait du fichier pdf
    """
    try:
        # Lecture du fichier uploadé directement depuis l'objet 'file'
        raw_file = BytesIO(await file.read())  # File est un objet avec un attribut 'read' pour récupérer son contenu
        
        # Détection automatique de l'encodage
        result = chardet.detect(raw_file.read())  # Lis tout le contenu du fichier pour détecter l'encodage
        encoding = result['encoding'] if result['confidence'] > 0.7 else 'utf-8'
        
        # Remise à zéro du pointeur de lecture du fichier
        raw_file.seek(0)

        # Lecture du fichier avec l'encodage détecté
        content = raw_file.read().decode(encoding, errors='replace')

        # Normaliser les fins de lignes
        content = re.sub(r'\r\n', '\n', content)

        return content
    except Exception as e:
        return f"Erreur spécifique à l'extraction texte: {e}"

async def generate_correction(text: str) -> str:
    """
    Génère un corrigé en utilisant Ollama.
    Args:
        text (str):Le texte traité.
    Returns:
        str: Correction générée.
    """
    prompt = f"""
Vous êtes un assistant spécialisé dans la correction d'examens et d'évaluations académiques. 
Voici les règles à suivre :
1. Répondez en français de manière claire, précise et concise.
2. Structurez la réponse pour permettre une comparaison facile avec les réponses des étudiants.
3. Si la question le nécessite, incluez du code en respectant les conventions syntaxiques adéquates.
4. Ne fournissez aucune explication supplémentaire, uniquement le contenu attendu.
5. Adaptez la réponse au niveau de détail demandé par la question, ni plus, ni moins.

Texte de la question : {text}
"""

    # Demande de correction à Ollama
    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]
    )
    
    # Récupération de la réponse
    corrected_text = response["message"]["content"]

    # Après avoir obtenu la réponse, nettoyage des éléments indésirables
    # Supprimer ce qui est entre <think> et </think>
    cleaned_text = re.sub(r"<think>.*?</think>", "", corrected_text)
    # Supprime les balises HTML restantes
    content = re.sub(r"<.*?>", "", cleaned_text)
    # Remplace les espaces multiples et normalise
    content = re.sub(r"\s+", " ", cleaned_text)
    # Supprimer exactement "###", "#####", "```sql", "**" et "---"
    cleaned_text = re.sub(r"###", "", cleaned_text)  # Supprime les "###"
    cleaned_text = re.sub(r"#####", "", cleaned_text)  # Supprime les "#####"
    cleaned_text = re.sub(r"```sql", "", cleaned_text)  # Supprime "```sql"
    cleaned_text = re.sub(r"\*\*", "", cleaned_text)  # Supprime les "**"
    cleaned_text = re.sub(r"---", "", cleaned_text)  # Supprime les "---"

    return cleaned_text


def create_pdf_from_text(text: str) -> bytes:
    """
    Crée un PDF avec des marges réduites et un meilleur formatage.
    Args:
        text (str):Le texte traité.
    Returns:
        bytes: Le fichier en format binaire
    """
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
    """
    Compare le devoir de l'étudiant avec la correction du professeur et génère une note et justification.

    Args:
        devoir_text:(str):Le devoir de l'élève.
        bytes: La correction unique du devoir.
    Returns:
        correction_text:(str): La correction unique du devoir.
    """
    prompt = f"""
    Vous êtes un professeur qui note les réponses des élèves selon ces critères stricts :

1. Langue et structure :
   - Répondez toujours en français, de manière claire, précise et concise.
   - Corrigez chaque question en comparant la réponse de l'étudiant à la correction de cette question .

2. Notation :
   - Évaluez uniquement la compréhension conceptuelle, pas la formulation exacte.
   - Donnez une note sous forme d'un nombre décimal
     - Réponse complètement fausse ou hors sujet: 0
     - Réponse parfaitement correcte : Toute la question est correctement répondue, donc la réponse obtient tous les points de la question.
     - Réponse partiellement correcte : Notez proportionnellement suivant le barème, par exemple 75% du barème, 50% du barème, ou 25% du barème, selon les éléments manquants ou incomplets.
     - Pour les valeurs intermédiaires, soyez précis (exemple : 0.25, 0.6, 0.85).
   - Justification : 
     -Pour chaque réponse corrigée, fournissez une justification brève en français, expliquant pourquoi la réponse est correcte ou partiellement correcte.
     - Ne fournissez aucun commentaire, explication ou justification détaillée au-delà de la note et de la brève justification.
   - Soyez cohérent et objectif dans votre notation.

3. Code :
   - Si le code est demandé, évaluez sa logique et son exactitude (correctitude syntaxique et fonctionnelle).
   - En l'absence de barème précis, basez-vous sur la correction attendue du sujet et la précision de la réponse donnée.
   - Si une réponse nécessite une démonstration technique, assurez-vous que la logique et le format du code soient corrects.

   **Correction des questions :**
    {correction_text}
    ---  
    **Devoir de l'etudiant :**  
    {devoir_text}
    """
    
    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Correction : {str(correction_text)}\nDevoir de l'étudiant : {str(devoir_text)}"}
        ]
    )


    corrected_text = response["message"]["content"]

    # Nettoyage des balises non souhaitées
    cleaned_text = re.sub(r"<think>.*?</think>", "", corrected_text)  # Supprime les balises HTML/XML
    cleaned_text = re.sub(r"###|#####|```sql|```|\*\*|---", "", cleaned_text)  # Supprime les caractères spécifiés
    return cleaned_text.strip()








