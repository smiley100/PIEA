import ollama

def summarize_text(text: str) -> str:

    """
    Résume un texte en utilisant Ollama et deepseek-r1:7b.
    :param text: Texte à résumer
    :return: Résumé généré
    """

    try:
        response = ollama.chat(
            model = "deepseek-r1:7b",
            messages=[
                {
                    "role": "user",
                    "content": f"Résumé ce texte en 1 à 2 phrase : {text}"
                }
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Erreur lors de l'appel à Ollama: {e}"