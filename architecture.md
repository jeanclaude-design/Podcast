# Architecture Générale - Projet Podcastify

## 1. Vue d'Ensemble

Le projet Podcastify est conçu comme un pipeline de traitement de données modulaire, où chaque composant a une responsabilité unique. L'architecture vise à découpler l'extraction, la transformation et la génération du contenu, permettant une maintenance et une évolution plus faciles.

L'orchestration de ce pipeline est gérée par un `Makefile`, qui sert de point d'entrée pour l'utilisateur et assure que les différentes étapes sont exécutées dans le bon ordre.

Le flux de données est le suivant :
**Source (PDF, URL, etc.)** -> **Extraction** -> **Texte Brut** -> **Synthèse IA** -> **Dialogue Structuré** -> **Synthèse Vocale** -> **Fichier Audio MP3**

## 2. Composants Principaux

Le système est articulé autour de trois composants logiques principaux, chacun matérialisé par un ou plusieurs scripts Python.

### 2.1. Module d'Extraction (`Extraction.py`)

Ce module est la porte d'entrée des données. Sa seule responsabilité est de prendre une source (un fichier local, une URL) et d'en extraire le contenu textuel brut.

-   **Interface** : Il est conçu autour d'une classe de base abstraite (`TextExtractor`) et de plusieurs implémentations concrètes, chacune spécialisée pour un type de source (PDF, YouTube, Web, etc.).
-   **Dispatcher** : Un mécanisme de détection (`detect_source`) analyse l'entrée pour sélectionner dynamiquement l'extracteur approprié. Cela rend le système extensible : pour supporter une nouvelle source, il suffit d'ajouter une nouvelle classe d'extraction.
-   **Sortie** : Il produit des fichiers JSON et Markdown contenant le texte extrait et des métadonnées de base (comme le titre), qui sont stockés dans le dossier `output/`.

### 2.2. Module de Synthèse (`test_synthese_pdf.py`)

Ce composant agit comme une couche de transformation intermédiaire. Il prend le texte brut extrait par le premier module et le prépare pour la vocalisation.

-   **Rôle** : Sa fonction principale est de synthétiser et de structurer le texte. Il peut appliquer des filtres, résumer le contenu ou le reformater pour qu'il soit plus adapté à un format de dialogue.
-   **Dépendance** : Il consomme les fichiers JSON produits par le module d'extraction.
-   **Sortie** : Il génère des fichiers Markdown (`.md`) qui contiennent le texte final prêt à être transformé en dialogue.

### 2.3. Module de Vocalisation (`podcastify.py`)

C'est le dernier maillon de la chaîne. Il transforme le contenu textuel final en un produit audio.

-   **Génération de Dialogue** : Il envoie le texte synthétisé à un modèle de langage (GPT-4o-mini) avec des instructions spécifiques pour le convertir en un dialogue à deux voix.
-   **Synthèse Vocale** : Il prend chaque ligne du dialogue généré et appelle l'API de synthèse vocale d'OpenAI pour créer les segments audio.
-   **Assemblage Audio** : Il concatène les différents segments audio pour former un unique fichier MP3.
-   **Sortie** : Il produit le fichier audio final (`.mp3`) et sa transcription textuelle (`.txt`).

## 3. Orchestration (`Makefile`)

Le `Makefile` est le chef d'orchestre du projet. Il définit les dépendances entre les différentes étapes et fournit une interface utilisateur simple et cohérente.

-   **Cibles** : Il définit des cibles claires (`convert`, `synthese`, `podcastify`, `all`, `clean`) qui correspondent aux différentes étapes logiques du pipeline.
-   **Paramétrage** : Il permet de configurer l'exécution via des variables (ex: `PDF`, `XLSX_FILE`, `VOICE1`, `MODEL`), ce qui évite de devoir modifier les scripts directement.
-   **Gestion des Dépendances** : Il s'assure, par exemple, que l'étape `synthese` ne peut pas être lancée avant que l'étape `convert` n'ait produit les fichiers nécessaires.

## 4. Diagramme de Flux Architectural

```mermaid
graph TD
    subgraph "Input"
        A[Fichier PDF]
        B[Fichier Excel d'URLs]
        C[URL unique]
    end

    subgraph "Orchestration (Makefile)"
        D{make all/convert}
    end

    subgraph "1. Extraction (Extraction.py)"
        E[Détection de la source] --> F{Choix de l'extracteur};
        F --> G[Extracteur PDF/OCR];
        F --> H[Extracteur URL];
        F --> I[Extracteur YouTube];
        G & H & I --> J[Génération de JSON/MD bruts];
    end

    subgraph "2. Synthèse (test_synthese_pdf.py)"
        K{make synthese} --> L[Lecture des JSON];
        L --> M[Synthèse du texte];
        M --> N[Génération de MD synthétisés];
    end

    subgraph "3. Vocalisation (podcastify.py)"
        O{make podcastify} --> P[Lecture des MD synthétisés];
        P --> Q[Génération de dialogue via IA];
        Q --> R[Synthèse vocale via API];
        R --> S[Assemblage du fichier MP3];
    end

    subgraph "Output"
        T[Fichier Audio .mp3]
        U[Transcription .txt]
    end

    A & B & C --> D;
    D --> E;
    J --> K;
    N --> O;
    S --> T & U;