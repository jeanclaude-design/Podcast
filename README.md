# Projet Podcastify : Générateur de Contenu Audio Automatisé

Ce projet transforme diverses sources de contenu (PDF, articles web, vidéos YouTube) en podcasts audio à deux voix. Il utilise une chaîne d'outils pour extraire, synthétiser et vocaliser l'information, le tout orchestré par un `Makefile` pour une utilisation simplifiée.

## Fonctionnalités

-   **Extraction Multi-Source** : Capable d'extraire du texte depuis des fichiers locaux (PDF, DOCX, TXT, MD), des URLs d'articles, des vidéos YouTube et même d'utiliser l'OCR pour les PDF scannés.
-   **Synthèse par IA** : Utilise un modèle de langage (GPT-4o-mini) pour transformer le contenu extrait en un dialogue fluide et naturel entre deux intervenants.
-   **Vocalisation de Haute Qualité** : Génère un fichier audio MP3 à partir du dialogue en utilisant les voix de l'API de synthèse vocale d'OpenAI.
-   **Orchestration Simplifiée** : Un `Makefile` permet de lancer l'ensemble du processus (extraction, synthèse, vocalisation) avec des commandes simples.
-   **Gestion de Sources Multiples** : Peut traiter un fichier unique ou une liste d'URLs fournie dans un fichier Excel.

## Prérequis

-   Python 3.8+
-   Les dépendances listées dans `requirements.txt` (à créer).
-   Un fichier `.env` à la racine du projet contenant votre clé `OPENAI_API_KEY` et potentiellement `MISTRAL_API_KEY` si vous utilisez l'OCR Mistral.
    ```
    OPENAI_API_KEY="sk-..."
    MISTRAL_API_KEY="sk-..."
    ```

## Structure du Projet

-   `Extraction.py`: Script principal pour l'extraction de contenu depuis diverses sources.
-   `podcastify.py`: Script pour transformer un texte en dialogue et le convertir en fichier audio MP3.
-   `test_synthese_pdf.py`: Script (probablement un outil intermédiaire) pour synthétiser le contenu extrait avant la vocalisation.
-   `Makefile`: Fichier d'orchestration pour automatiser les différentes étapes du processus.
-   `output/`: Dossier où tous les fichiers générés (textes, JSON, MD, MP3) sont sauvegardés.

## Utilisation

Le `Makefile` est le point d'entrée principal. Voici les commandes les plus courantes :

1.  **Pour traiter un seul fichier PDF** :
    ```bash
    make all PDF="chemin/vers/mon/fichier.pdf"
    ```
    Cette commande va enchaîner l'extraction, la synthèse et la création du podcast pour le PDF spécifié.

2.  **Pour traiter une liste d'URLs depuis un fichier Excel** :
    Assurez-vous que votre fichier Excel (par ex. `liste_urls.xlsx`) contient une colonne nommée "URL".
    ```bash
    make all XLSX_FILE="liste_urls.xlsx"
    ```

3.  **Exécuter les étapes séparément** :
    -   `make convert [PDF="..."] [XLSX_FILE="..."]`: Uniquement l'étape d'extraction.
    -   `make synthese [PDF="..."]`: Uniquement l'étape de synthèse (nécessite que `convert` ait été lancé avant).
    -   `make podcastify [PDF="..."]`: Uniquement la création du podcast (nécessite que `synthese` ait été lancé avant).

4.  **Nettoyer les fichiers générés** :
    ```bash
    make clean
    ```
    Cette commande supprime le dossier `output/` et tout son contenu.

## Personnalisation

Vous pouvez personnaliser les voix, le modèle de synthèse vocale et le template de dialogue en passant des variables au `Makefile` :

```bash
make podcastify PDF="mon.pdf" VOICE1="nova" VOICE2="shimmer" TEMPLATE="lecture"