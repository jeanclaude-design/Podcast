# coding: utf-8
import argparse
import os
import re
import json
from urllib.parse import urlparse
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi as YT, NoTranscriptFound, TranscriptsDisabled
from trafilatura import fetch_url, extract as trafilatura_extract
import nbformat
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from mistralai import Mistral, DocumentURLChunk
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# === Extracteurs ===
class TextExtractor(ABC):
    @abstractmethod
    def extract(self, url: str) -> Optional[Union[str, dict]]:
        pass

class VideoExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[dict]:
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
        title = self.get_youtube_title(video_id)
        try:
            transcript_list = YT.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(['fr'])
            except NoTranscriptFound:
                transcript = transcript_list.find_transcript(['en'])
            text = " ".join([entry["text"] for entry in transcript.fetch()])
            return {"title": title, "text": text}
        except (NoTranscriptFound, TranscriptsDisabled):
            return None

    def extract_video_id(self, url: str) -> Optional[str]:
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return None

    def get_youtube_title(self, video_id: str) -> str:
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = requests.get(oembed_url)
            return response.json().get("title", "video")
        except Exception:
            return "video"

class TrafilaturaExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        return trafilatura_extract(fetch_url(url))

class PDFLocalExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        reader = PdfReader(url)
        return "".join(page.extract_text() or "" for page in reader.pages)

class PDFTelechargeExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        filename = "temp_downloaded.pdf"
        with open(filename, "wb") as f:
            f.write(requests.get(url).content)
        reader = PdfReader(filename)
        os.remove(filename)
        return "".join(page.extract_text() or "" for page in reader.pages)

class PDFLocalImageExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        images = convert_from_path(url)
        return "".join(pytesseract.image_to_string(img) for img in images)

class BeautifulSoupExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        soup = BeautifulSoup(requests.get(url).content, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))

class ColabLocalExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        with open(url, "r", encoding="utf-8") as f:
            notebook = nbformat.read(f, as_version=4)
        return "\n".join(cell.source for cell in notebook.cells if cell.cell_type in ("markdown", "code"))

class ColabTelechargeExtractor(TextExtractor):
    def extract(self, url: str) -> Optional[str]:
        filename = "temp_notebook.ipynb"
        with open(filename, "wb") as f:
            f.write(requests.get(url).content)
        with open(filename, "r", encoding="utf-8") as f:
            notebook = nbformat.read(f, as_version=4)
        os.remove(filename)
        return "\n".join(cell.source for cell in notebook.cells if cell.cell_type in ("markdown", "code"))

class PDFOcrMistralExtractor(TextExtractor):
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")

    def extract(self, url: str) -> Optional[str]:
        client = Mistral(api_key=self.api_key)
        path = Path(url)
        uploaded = client.files.upload(file={"file_name": path.name, "content": path.read_bytes()}, purpose="ocr")
        signed_url = client.files.get_signed_url(file_id=uploaded.id, expiry=1)
        ocr_result = client.ocr.process(document=DocumentURLChunk(document_url=signed_url.url), model="mistral-ocr-latest")
        data = json.loads(ocr_result.model_dump_json())
        fic =  "\n".join(block["text"] for block in data.get("chunks", []))
        return data

class PDFTelechargeOcrMistralExtractor(TextExtractor):
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("La clé MISTRAL_API_KEY est manquante.")

    def extract(self, url: str) -> Optional[str]:
        filename = "temp_downloaded_ocr.pdf"
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            print(f"🔽 Téléchargement de : {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"✅ PDF téléchargé : {len(response.content)} octets")

            client = Mistral(api_key=self.api_key)
            path = Path(filename)
            uploaded = client.files.upload(
                file={"file_name": path.name, "content": path.read_bytes()},
                purpose="ocr",
            )
            signed_url = client.files.get_signed_url(file_id=uploaded.id, expiry=1)
            ocr_result = client.ocr.process(
                document=DocumentURLChunk(document_url=signed_url.url),
                model="mistral-ocr-latest",
            )
            os.remove(filename)

            data = json.loads(ocr_result.model_dump_json())
            fic ="\n".join(block["text"] for block in data.get("chunks", []))
            return data

        except requests.HTTPError as e:
            print(f"❌ Erreur HTTP lors du téléchargement : {e}")
        except Exception as e:
            print(f"❌ Erreur inattendue pendant l'extraction OCR : {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

        return None

# === Dispatcher et extraction
def detect_source(url: str, ocr: bool) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if url.endswith(".pdf") and url.startswith("http"):
        return "pdf_telecharge_ocr" if ocr else "pdf_telecharge"
    if url.endswith(".pdf"):
        return "pdf_local_ocr" if ocr else "pdf_local"
    if url.endswith(".ipynb") and url.startswith("http"):
        return "colab_telecharge"
    if url.endswith(".ipynb"):
        return "colab_local"
    if url.startswith("http"):
        return "trafilatura"
    return "autre"

def get_extractor(source: str):
    sources_extracteurs = {
        "youtube": VideoExtractor,
        "trafilatura": BeautifulSoupExtractor,
        "pdf_telecharge": PDFTelechargeExtractor,
        "pdf_local": PDFLocalExtractor,
        "pdf_telecharge_ocr": PDFTelechargeOcrMistralExtractor,
        "pdf_local_ocr": PDFOcrMistralExtractor,
        "autre": BeautifulSoupExtractor,
        "colab_local": ColabLocalExtractor,
        "colab_telecharge": ColabTelechargeExtractor,
        "pdf_image": PDFLocalImageExtractor,
    }
    extractor_class = sources_extracteurs.get(source)
    if extractor_class is None:
        raise ValueError(f"Source non supportée : {source}")
    return extractor_class()

def extrait(url: str, ocr: bool = False) -> Optional[dict]:
    source = detect_source(url, ocr)
    extractor = get_extractor(source)
    result = extractor.extract(url)
   
    # Si l'extracteur retourne un texte brut, on l'encapsule dans un dict
    if isinstance(result, str):
        parsed_url = urlparse(url)
        raw_title = os.path.basename(parsed_url.path) or "document"
        return {
            "title": raw_title,
            "text": result
        }
    # Sinon on retourne directement (si déjà un dict)
 
    return result

def format_markdown(text: str) -> str:
    lines = text.splitlines()
    formatted_lines = []

    for l in lines:
        l_stripped = l.strip()
        if not l_stripped:
            continue  # Ignore les lignes vides

        # Debug: Imprimer la ligne actuelle
        #print(f"Processing line: {l_stripped}")

        if l_stripped.isupper() and len(l_stripped.split()) < 8:
            formatted_lines.append(f"# {l_stripped}\n")
        elif re.match(r"https?://", l_stripped):
            formatted_lines.append(f"[Lien]({l_stripped})\n")
        else:
            formatted_lines.append(f"{l_stripped}\n")

    return "".join(formatted_lines)


def sanitize_filename(name: str) -> str:
    """Nettoie une chaîne pour en faire un nom de fichier sûr."""
    return re.sub(r'\W+', '_', name).strip('_') or "document"

def process_urls(urls: list, ocr: bool):
    processed_urls = set()  # Utiliser un ensemble pour suivre les URLs traitées

    for url in urls:
        # Vérifie si l'URL est valide
        if not re.match(r'https?://', url):
            print(f"URL invalide ignorée : {url}")
            continue

        # Vérifie si l'URL a déjà été traitée
        if url in processed_urls:
            print(f"URL déjà traitée : {url}")
            continue

        processed_urls.add(url)  # Ajoute l'URL à l'ensemble des URLs traitées

        print(f"\n🔄 Extraction OCR ou texte à partir de {url}...")
        result = extrait(str(url), ocr=ocr)

        if not result:
            print("❌ Aucun résultat.")
            continue

        # Récupération du texte extrait
        text = result.get("text")

        # Cas OCR : extraire depuis pages[]
        if not text and "pages" in result:
            text = "\n\n".join(p.get("markdown", "") for p in result["pages"])

        if not text or not text.strip():
            print("❌ Aucune donnée extraite.")
            continue

        # Déterminer le titre
        raw_title = result.get("title")
        if not raw_title:
            parsed_url = urlparse(url)
            raw_title = os.path.basename(parsed_url.path)

        # Nettoyage du titre pour nom de fichier
        safe_title = re.sub(r'\W+', '_', raw_title).strip('_')

        # Chemins de sortie
        output_md_path = Path(f"output/{safe_title}.md")
        output_json_path = Path(f"output/{safe_title}.json")

        # Sauvegarde Markdown
        markdown_text = format_markdown(text)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        print(f"✅ Markdown : {output_md_path}")

        # Sauvegarde JSON format synthèse
        pages_json = {
            "pages": [
                {
                    "index": 0,
                    "markdown": markdown_text
                }
            ]
        }
        with open(output_json_path, "w", encoding="utf-8") as jf:
            json.dump(pages_json, jf, ensure_ascii=False, indent=2)
        print(f"✅ JSON : {output_json_path}")



def main():
    parser = argparse.ArgumentParser(description="Extracteur universel 🧠")
    parser.add_argument("input", help="URL ou chemin du fichier XLSX contenant les URLs")
    parser.add_argument("--ocr", action="store_true", help="Activer OCR")
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)

    input_path = args.input
    if input_path.endswith(".xlsx"):
        # Lire les URLs depuis le fichier XLSX
        df = pd.read_excel(input_path)
        #urls = df.iloc[:, 0].astype(str).tolist()  # Convertir les Timestamp en chaînes de caractères
        # Vérifier si la colonne "URL" existe dans le DataFrame
        if "URL" in df.columns:
            urls = df["URL"].astype(str).tolist()  # Convertir les URLs en chaînes de caractères
            process_urls(urls, args.ocr)
        else:
            print("La colonne 'URL' n'existe pas dans le fichier Excel.")
        process_urls(urls, args.ocr)
    else:
        # Traiter une seule URL
        process_urls([input_path], args.ocr)

if __name__ == "__main__":
    #input_path="https://levelup.gitconnected.com/the-guide-to-mcp-i-never-had-f79091cf99f8?gi=743c7d82d5cd"
    #process_urls([input_path], False)
   main()




