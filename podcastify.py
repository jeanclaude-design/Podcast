import os
import sys
import io
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import docx2txt
from templates import INSTRUCTION_TEMPLATES

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

SUPPORTED_EXTS = [".pdf", ".md", ".txt", ".docx"]

def extract_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif ext in [".md", ".txt"]:
        return file_path.read_text(encoding="utf-8")
    elif ext == ".docx":
        return docx2txt.process(str(file_path))
    else:
        raise ValueError(f"❌ Type de fichier non supporté : {ext}")

def generate_dialogue(text: str, template_key: str) -> str:
    template = INSTRUCTION_TEMPLATES[template_key]

    prompt = f"""{template['intro']}

Voici le texte d'entrée :

<texte>
Langue : Français

{text}
</texte>

{template['text_instructions']}

<scratchpad>
{template['scratch_pad']}
</scratchpad>

{template['prelude']}

Vous allez maintenant rédiger un dialogue entre deux interlocuteurs nommés "speaker-1" et "speaker-2".
Chaque ligne commence par l’étiquette de l'interlocuteur, suivie d’un deux-points. Par exemple :
speaker-1: Bonjour, comment vas-tu ?
speaker-2: Très bien merci, et toi ?

<podcast_dialogue>
{template['dialog']}
</podcast_dialogue>
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un créateur de podcasts en français. Tu produis des dialogues à deux voix."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
    )
    return response.choices[0].message.content

def split_dialogue(text: str):
    lines = text.strip().splitlines()
    dialogue = []
    for line in lines:
        if line.startswith("speaker-1:") or line.startswith("speaker-2:"):
            speaker, speech = line.split(":", 1)
            dialogue.append((speaker.strip(), speech.strip()))
    return dialogue

def dialogue_to_audio_bytes(dialogue: list, voice1="alloy", voice2="echo", audio_model="tts-1") -> bytes:
    audio = b""
    for idx, (speaker, speech) in enumerate(dialogue):
        if not speech.strip():
            print(f"⚠️ Ligne vide ignorée à l'index {idx}")
            continue

        voice = voice1 if speaker == "speaker-1" else voice2
        print(f"🎙️ Synthèse ligne {idx} [{speaker} - {voice}] → \"{speech[:60]}...\"")

        try:
            with client.audio.speech.with_streaming_response.create(
                model=audio_model,
                voice=voice,
                input=speech,
                response_format="mp3"
            ) as response:
                for chunk in response.iter_bytes():
                    audio += chunk
        except Exception as e:
            print(f"❌ Échec synthèse [{speaker}] : {e}")
            continue

    if not audio:
        print("🧨 Aucun chunk reçu !")
        raise ValueError("❌ Aucun audio généré. Vérifiez les lignes ou la connexion à l’API.")

    return audio



def save_files(base_name: str, audio: bytes, transcript: str):
    Path("output").mkdir(exist_ok=True)
    audio_path = Path(f"output/{base_name}_audio.mp3")
    text_path = Path(f"output/{base_name}_transcription.txt")
    audio_path.write_bytes(audio)
    text_path.write_text(transcript, encoding="utf-8")
    print(f"\n✅ Audio : {audio_path.resolve()}")
    print(f"📄 Transcription : {text_path.resolve()}")

def main():
    parser = argparse.ArgumentParser(description="🎙️ Génère un podcast ou une conférence à partir d’un fichier texte.")
    parser.add_argument("--input", "-i", required=True, help="Fichier source (.pdf, .md, .txt, .docx)")
    parser.add_argument("--template", "-t", default="podcast (French)", help="Template à utiliser (ex: podcast (French), lecture, summary)")
    parser.add_argument("--voice1", default="alloy", help="Voix pour speaker-1")
    parser.add_argument("--voice2", default="echo", help="Voix pour speaker-2")
    parser.add_argument("--audio-model", default="tts-1", help="Modèle audio OpenAI (tts-1, tts-1-hd, gpt-4o-mini-tts)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists() or input_path.suffix.lower() not in SUPPORTED_EXTS:
        print("❌ Fichier introuvable ou non supporté.")
        sys.exit(1)

    print("📖 Lecture du fichier...")
    text = extract_text(input_path)

    print(f"🧠 Génération du dialogue ({args.template})...")
    transcript = generate_dialogue(text, args.template)

    print("🔍 Analyse du dialogue...")
    dialogue_lines = split_dialogue(transcript)

    print("🔊 Synthèse vocale...")
    audio = dialogue_to_audio_bytes(dialogue_lines, voice1=args.voice1, voice2=args.voice2, audio_model=args.audio_model)

    base = input_path.stem
    save_files(base, audio, transcript)

if __name__ == "__main__":
    main()

