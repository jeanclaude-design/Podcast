# Architecture Détaillée - Projet Podcastify

Ce document détaille l'implémentation technique de chaque composant du projet Podcastify.

## 1. Module d'Extraction (`Extraction.py`)

Ce module est conçu selon le principe de la responsabilité unique et le patron de conception Stratégie. Une classe de base abstraite définit le contrat, et des classes concrètes implémentent les différentes stratégies d'extraction.

### 1.1. Classes d'Extraction

-   **`TextExtractor(ABC)`** : Classe de base abstraite.
    -   `extract(self, url: str) -> Optional[Union[str, dict]]`: Méthode abstraite que toutes les sous-classes doivent implémenter.

-   **Implémentations Concrètes** :
    -   `VideoExtractor`: Gère les URLs YouTube. Utilise `youtube_transcript_api` pour récupérer les transcriptions. Retourne un dictionnaire `{"title": ..., "text": ...}`.
    -   `TrafilaturaExtractor`: Extracteur générique pour les articles web. Utilise la bibliothèque `trafilatura`.
    -   `PDFLocalExtractor`: Lit le texte d'un fichier PDF local avec `PyPDF2`.
    -   `PDFTelechargeExtractor`: Télécharge un PDF depuis une URL avant de l'analyser avec `PyPDF2`.
    -   `PDFLocalImageExtractor`: Utilise `pdf2image` et `pytesseract` pour effectuer un OCR local sur un PDF. (Moins performant que l'API Mistral).
    -   `PDFOcrMistralExtractor` / `PDFTelechargeOcrMistralExtractor`: Les stratégies les plus avancées pour l'OCR. Elles envoient le fichier PDF (local ou téléchargé) à l'API Mistral pour une reconnaissance de caractères de haute qualité.
    -   `ColabLocalExtractor` / `ColabTelechargeExtractor`: Spécifiques aux notebooks Jupyter (.ipynb), extraient le contenu des cellules de code et de markdown.

### 1.2. Dispatcher et Fonctions Utilitaires

-   **`detect_source(url: str, ocr: bool) -> str`**:
    -   Analyse la chaîne `url` (format, préfixe http, etc.) et le booléen `ocr` pour déterminer quelle stratégie d'extraction utiliser.
    -   Retourne une chaîne de caractères (ex: `"youtube"`, `"pdf_local_ocr"`) qui sert de clé pour le dispatcher.

-   **`get_extractor(source: str) -> TextExtractor`**:
    -   Fonction "factory" qui prend la clé de source en entrée et retourne une instance de la classe d'extraction correspondante.

-   **`extrait(url: str, ocr: bool = False) -> Optional[dict]`**:
    -   Fonction principale du module.
    -   Orchestre l'appel à `detect_source` et `get_extractor`.
    -   Appelle la méthode `extract()` de l'instance choisie.
    -   Standardise la sortie en un dictionnaire `{"title": ..., "text": ...}`.

-   **`process_urls(urls: list, ocr: bool)`**:
    -   Itère sur une liste d'URLs (provenant de la ligne de commande ou d'un fichier Excel).
    -   Appelle `extrait()` pour chaque URL.
    -   Gère la sauvegarde des résultats aux formats `.md` et `.json` dans le dossier `output/`.
    -   Utilise `sanitize_filename()` pour créer des noms de fichiers valides.

## 2. Module de Vocalisation (`podcastify.py`)

Ce script est un pipeline linéaire qui prend un fichier texte en entrée et produit un fichier audio.

### 2.1. Fonctions Clés

-   **`extract_text(file_path: Path) -> str`**:
    -   Fonction de lecture de fichier source, supportant .pdf, .md, .txt, .docx. C'est une version simplifiée de l'extraction, utilisée ici pour lire le fichier de synthèse `.md` généré par l'étape précédente.

-   **`generate_dialogue(text: str, template_key: str) -> str`**:
    -   Construit un prompt détaillé pour l'API OpenAI (GPT-4o-mini) en utilisant un template.
    -   Le prompt instruit l'IA de transformer le texte d'entrée en un dialogue à deux voix.
    -   Retourne la réponse brute de l'IA contenant le dialogue.

-   **`split_dialogue(text: str) -> list`**:
    -   Parse la sortie textuelle de l'IA.
    -   Sépare chaque ligne en un tuple `(speaker, speech)`.
    -   Retourne une liste de ces tuples, par exemple `[('speaker-1', 'Bonjour...'), ('speaker-2', 'Salut !')]`.

-   **`dialogue_to_audio_bytes(dialogue: list, ...)`**:
    -   Itère sur la liste de tuples de dialogue.
    -   Pour chaque ligne, appelle l'API de synthèse vocale d'OpenAI (`client.audio.speech`) avec la voix appropriée (`voice1` ou `voice2`).
    -   Utilise le mode streaming (`with_streaming_response`) pour recevoir l'audio par chunks.
    -   Concatène les chunks de bytes audio pour former le fichier final.
    -   Retourne l'objet `bytes` complet de l'audio.

-   **`save_files(base_name: str, audio: bytes, transcript: str)`**:
    -   Crée le dossier `output/` si nécessaire.
    -   Sauvegarde les bytes audio dans un fichier `.mp3`.
    -   Sauvegarde la transcription du dialogue dans un fichier `.txt`.

-   **`main()`**:
    -   Gère les arguments de la ligne de commande (`argparse`) pour la configuration (fichier d'entrée, voix, modèle).
    -   Appelle séquentiellement toutes les fonctions ci-dessus pour exécuter le pipeline complet.

## 3. Orchestration (`Makefile`)

Le `Makefile` est le liant du projet. Il utilise des règles et des variables pour automatiser l'exécution des scripts Python.

-   **Variables (`?=`)**: `PDF`, `XLSX_FILE`, `VOICE1`, `VOICE2`, `MODEL`, etc. sont définies avec `?=` pour permettre leur surcharge depuis la ligne de commande (ex: `make all PDF=mon.pdf`).
-   **Cibles Phony (`.PHONY`)**: `all`, `convert`, `synthese`, `podcastify`, `clean` sont déclarées comme "phony" car elles ne correspondent pas à des noms de fichiers réels. Ce sont des commandes.
-   **Logique Conditionnelle**: Le `Makefile` utilise des structures `if/else` en shell pour adapter son comportement. Par exemple, la cible `convert` exécute une commande différente si la variable `PDF` est définie ou si `XLSX_FILE` est utilisé.
-   **Gestion des Fichiers**: Il manipule directement les fichiers de sortie, par exemple en listant les `.json` dans `output/` pour les passer à l'étape `synthese`, ou en lisant un fichier `meta_title.txt` pour nommer correctement les sorties.
-   **Flux d'Exécution**:
    1.  `make convert`: Lance `Extraction.py` sur la source (PDF ou URLs).
    2.  `make synthese`: Itère sur les `.json` créés et lance `test_synthese_pdf.py` sur chacun pour créer les `.md`.
    3.  `make podcastify`: Lance `podcastify.py` sur les `.md` créés pour générer les `.mp3`.
    4.  `make all`: Exécute les trois cibles ci-dessus dans l'ordre.