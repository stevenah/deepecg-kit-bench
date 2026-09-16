# DeepECG-Bench. `make check` is what CI runs; everything else is a step of it.
PY := python3
DEEPECG ?= ../deepecg-kit/.venv/bin/deepecg
KIT_REPO ?= ../deepecg-kit

.PHONY: help validate identifiers data build serve check clean registry snapshot

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | column -t -s "$$(printf '\t')"

validate: ## Run every integrity gate. Exits non-zero on any failure.
	$(PY) tools/validate.py --strict

identifiers: ## Resolve every DOI/arXiv id and check it names the paper we claim. Needs network.
	$(PY) tools/check_identifiers.py $(ARGS)

data: ## Build _data/generated/*.json and the inline SVG charts.
	$(PY) tools/build_site_data.py

build: data ## Build the site into _site/.
	bundle exec jekyll build --trace

serve: data ## Serve locally with live reload.
	bundle exec jekyll serve --livereload

check: validate data ## Validate, build data, run the tool tests.
	$(PY) -m pytest tools/tests -q

registry: ## Re-export _data/registry.json from an installed deepecgkit (needs torch).
	$(KIT_REPO)/.venv/bin/python tools/export_registry.py --kit-repo $(KIT_REPO)

clean:
	rm -rf _site .jekyll-cache _data/generated _includes/charts/generated
