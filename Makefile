PDF       ?= RelativitéGénérale.pdf
LANG      ?= fr_FR.utf8
MODEL     ?= tts-1
VOICE1    ?= alloy
VOICE2    ?= echo
TEMPLATE  ?= summary
XLSX_FILE ?= diff_new_emails.xlsx
URL_LIST  := output/urls.txt

META_FILE := output/meta_title.txt

.PHONY: all convert synthese podcastify clean

all: convert synthese podcastify

convert:
	@mkdir -p output
	@if [ -n "$(PDF)" ] && [ "$(PDF)" != "RelativitéGénérale.pdf" ]; then \
		echo "🔄 Extraction OCR ou texte à partir du PDF $(PDF)..."; \
		python3 Extraction.py "$(PDF)" --ocr; \
	else \
		echo "🔄 Lecture et déduplication des URLs depuis $(XLSX_FILE)..."; \
		python3 -c "import pandas as pd; df=pd.read_excel('$(XLSX_FILE)'); urls=df['URL'].dropna().drop_duplicates().tolist(); open('$(URL_LIST)','w').write('\\n'.join(urls))"; \
		echo "🔄 Extraction OCR ou texte à partir de chaque URL unique..."; \
		python3 -c "import subprocess; urls=open('$(URL_LIST)').read().splitlines(); [subprocess.run(['python3','Extraction.py',u,'--ocr'], check=False) for u in urls if u]"; \
	fi
	@echo "✅ Extraction terminée."

synthese:
	@mkdir -p output
	@if [ -n "$(PDF)" ] && [ "$(PDF)" != "RelativitéGénérale.pdf" ]; then \
		slug=$$(basename "$(PDF)" .pdf); \
		json_file=$$(ls output/*.json | grep "$$slug"); \
		if [ -f "$$json_file" ]; then \
			echo "📝 Synthèse de $$slug (PDF unique)..."; \
			cat "$$json_file" | python3 test_synthese_pdf.py --lang $(LANG) --pdf "$(PDF)" > output/$$slug.md || echo "⚠️ Échec de la synthèse pour $$slug"; \
		else \
			echo "❌ Le fichier $$json_file n'existe pas. Lance 'make convert PDF=\"$(PDF)\"' d'abord."; \
		fi \
	else \
		for json in output/*.json; do \
			[ -f "$$json" ] || continue; \
			slug=$$(basename "$$json" .json); \
			echo "📝 Synthèse de $$slug..."; \
			cat "$$json" | python3 test_synthese_pdf.py --lang $(LANG) --pdf "$(PDF)" > output/$$slug.md || echo "⚠️ Échec de la synthèse pour $$slug"; \
		done \
	fi
	@echo "✅ Synthèses terminées."

podcastify: $(META_FILE)
	@echo "🎙️ Création du podcast avec $(VOICE1) et $(VOICE2)..."
	@if [ -n "$(PDF)" ] && [ "$(PDF)" != "RelativitéGénérale.pdf" ]; then \
		TITLE=$$(basename "$(PDF)" .pdf); \
		SOURCE_MD="output/$$TITLE.md"; \
		if [ -f "$$SOURCE_MD" ]; then \
			echo "🎧 Fichier source : $$SOURCE_MD"; \
			python3 podcastify.py \
				-i "$$SOURCE_MD" \
				-t "$(TEMPLATE)" \
				--voice1 $(VOICE1) --voice2 $(VOICE2) \
				--audio-model $(MODEL); \
		else \
			echo "❌ Le fichier $$SOURCE_MD n'existe pas. Lance 'make synthese PDF=\"$(PDF)\"' d'abord."; \
		fi \
	else \
		TITLE=$$(cat $(META_FILE)); \
		SOURCE_MD="output/$$TITLE.md"; \
		echo "🎧 Fichier source : $$SOURCE_MD"; \
		python3 podcastify.py \
			-i "$$SOURCE_MD" \
			-t "$(TEMPLATE)" \
			--voice1 $(VOICE1) --voice2 $(VOICE2) \
			--audio-model $(MODEL); \
	fi
	@echo "✅ Podcast créé."

$(META_FILE):
	@echo "📁 Lecture du titre extrait depuis output/meta_title.txt..."
	@if [ -f output/meta_title.txt ]; then \
		cp output/meta_title.txt $(META_FILE); \
	else \
		echo "❌ Fichier output/meta_title.txt introuvable."; exit 1; \
	fi

clean:
	@echo "🧹 Nettoyage..."
	@rm -rf output
