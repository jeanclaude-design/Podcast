import sys
import os
import base64
from gradio_client import Client, FileData
from dotenv import load_dotenv

load_dotenv()

def read_markdown(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERREUR] Lecture fichier : {e}")
        return None

def encode_file_to_filedata(filepath, content):
    return FileData(
        b64=base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        filename=os.path.basename(filepath)
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_Podcast.py <fichier.md>")
        sys.exit(1)

    filepath = sys.argv[1]
    markdown_content = read_markdown(filepath)
    if not markdown_content:
        sys.exit(1)

    markdown_file = encode_file_to_filedata(filepath, markdown_content)

    client = Client("lamm-mit/PDF2Audio")

    # Construire les 18 paramètres requis
    inputs = [
    [markdown_file],                        # fichier
    "Test Markdown audio",                  # titre
    "o3-mini",                              # modèle
    "medium",                               # qualité
    False,                                  # zip
    "tts-1",                                # modèle vocal
    "alloy",                                # speaker 1
    "echo",                                 # speaker 2
    "Amical",                               # instructions 1
    "Sérieux",                              # instructions 2
    "Ceci est un test de contenu court.",   # param_10
    "Intro test",                           # param_11
    "Analyse test",                         # param_12
    "Idées test",                           # param_13
    "Structure test",                       # param_14
    "Dialogue test",                        # param_15
    "Résumé test",                          # param_16
    "Conclusion test"                       # param_17
    ]

    try:
        print("\n🚀 Envoi vers l'API `/validate_and_generate_audio`...")
        result = client.predict(*inputs, api_name="/validate_and_generate_audio")
        print("✅ Résultat reçu :")
        print(result)
    except Exception as e:
        print(f"[ERREUR API] {e}")



