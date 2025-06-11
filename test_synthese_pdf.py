# test_synthese_pdf.py
import os
import sys
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from markdown import markdown # Pour la conversion Markdown -> HTML
import tqdm # Pour la barre de progression
import re
import argparse
from pathlib import Path
load_dotenv()
def main ():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="fr", help="Langue de traitement")
    parser.add_argument("--pdf", required=True, help="Nom du fichier PDF source")
    args = parser.parse_args()   
    pdf_name = Path(args.pdf).stem

    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY manquant dans .env", file=sys.stderr)
        sys.exit(1)

    # Lit le JSON depuis stdin
    data = json.load(sys.stdin)

    try:
        pages = data["pages"]
        ocr_text = "\n\n".join(page.get("markdown", "") for page in pages)
    except KeyError:
        print("❌ Erreur : le champ 'pages' est manquant dans le JSON", file=sys.stderr)
        sys.exit(1)

    # Préfixe simple (à adapter avec un prompt plus élaboré)
    prompt = f"""Titre de l'article :** Propose un titre pertinent, clair et accrocheur sur le sujet abordé.
    - **Mots clés :** Identifie clairement 5 à 10 mots clés essentiels liés à l'article.
    - **Références :** Fournis une liste organisée de références à partir de sources fiables, en commençant impérativement par un article Wikipédia 
    puis en incluant des articles académiques, scientifiques ou de sites reconnus. Inclue les liens directs vers ces sources.
    - **Synthèse détaillée (3000 mots) :**
    - Rédige une synthèse complète et structurée en sections distinctes 
    - Rédige une synthèse complète et structurée en sections distinctes.
    -  Toute affirmation ou donnée présentée doit être impérativement sourcée en utilisant
        une notation de référence claire comme ceci : [1], avec à la fin une liste 
        précisant la référence et l'adresse URL complète de l'article.
    - Si l'article initial est insuffisant, complète impérativement en recherchant des informations supplémentaires 
    sur internet auprès de sources fiables, et précise clairement les ajouts effectués.
    - Évite toute répétition et veille à maintenir un style cohérent, détaillé et structuré, reflétant mon style personnel.
    - **Questions pertinentes :**
    - Propose une liste de 5 à 10 questions approfondies sur le sujet traité, facilitant la réflexion et la compréhension globale.
    - **Quiz interactif :**
    - Crée un quiz de 10 questions à choix multiples en intégrant impérativement l'ensemble des mots clés identifiés.
    - Propose pour chaque question 4 options possibles, en indiquant la bonne réponse en **gras**.
    Respecte rigoureusement les consignes et veille à livrer une réponse complète, documentée et directement exploitable.
    format de sortie Markdown.:

    {ocr_text}
    """

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash-preview-04-17"

    config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=64,
        max_output_tokens=65536,
        response_mime_type="text/plain",
    )
    contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
    full_response=""
    """
    for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
    ):      
            full_response += chunk.text
            print(chunk.text, end="")
    html_output = markdown(full_response)
    """

    # Estimation de la longueur de la réponse (approximative) - peut être ajustée
    estimated_length = len(prompt) * 5  # On estime que la réponse sera 5 fois plus longue que le prompt


    with tqdm.tqdm(total=estimated_length, unit="tokens", desc="Génération en cours") as pbar:
        full_response = "" # Accumule la réponse complète
        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config
        ):
            full_response += chunk.text  # Accumuler le texte
            pbar.update(len(chunk.text))  # Mettre à jour la barre de progression

        # Convertir le Markdown en HTML
        html_output = markdown(full_response)

    # Recherche du résumé long dans la réponse complète (expression régulière à ajuster si besoin)
    #summary_match = re.search(r"Synthèse détaillée \(3000 mots\) :[\s\n]*(.+?)[\n\n]+", full_response, re.DOTALL)
    #long_summary = summary_match.group(1).strip() if summary_match else ""

    short_summary=""      
    # Générer un résumé court à partir du résumé long (ici avec un prompt simple)
    short_summary_prompt = f"Résume ce texte en 1200 mots ou moins:\n\n{full_response}"
    short_summary_config = types.GenerateContentConfig(
                    temperature=0.5, # température plus basse pour plus de précision dans le résumé court
                    max_output_tokens=8192,
                )

    short_summary_contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=short_summary_prompt),
                    ],
                ),
            ]
    short_summary_response = ""
    for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=short_summary_contents,
                    config=short_summary_config,
                ):
                    short_summary_response += chunk.text
    short_summary = short_summary_response.strip() # Résumé court final
    print ( " Resumé court: \n ", short_summary)


    # --- Enregistrement des sorties ---
    # Sauvegarde des fichiers avec nom du PDF
    Path(f"{pdf_name}.md").write_text(full_response, encoding="utf-8")
    Path(f"{pdf_name}.html").write_text(html_output, encoding="utf-8")
    Path(f"{pdf_name}_short.md").write_text(short_summary, encoding="utf-8")
    print(f"✅ Fichiers générés : {pdf_name}.md, {pdf_name}.html, {pdf_name}_short.md")

if __name__ == "__main__":
    main()