# DeepECG-Bench. The page in site/ is static: nothing here builds it. These targets
# preview it, test it, and refresh the two generated data files.
KIT_REPO ?= ../deepecg-kit
DEEPECG  ?= $(KIT_REPO)/.venv/bin/deepecg
PORT     ?= 4000

.PHONY: help serve check registry results

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | column -t -s "$$(printf '\t')"

serve: ## Preview the page at http://localhost:4000/ (it fetches its data, so file:// will not do).
	python3 -m http.server $(PORT) --bind 127.0.0.1 --directory site

check: ## Run every test: data joins, the results tool, styles, page logic, and a browser smoke test.
	uv run pytest -q
	@if command -v node >/dev/null; then node --test tools/tests/app.test.mjs; \
	else echo "node not found: page-logic tests skipped (CI runs them)"; fi

registry: ## Re-export site/data/registry.json from the kit checkout (needs its venv, with torch).
	$(KIT_REPO)/.venv/bin/python tools/export_registry.py --kit-repo $(KIT_REPO)

# Give AGG to publish an existing `deepecg aggregate` output directory (the journal
# pipeline's, so the page shows the article's numbers), or RUNS to aggregate run
# directories first. RUNS with AGG only says where to copy the diagnostic plots from.
results: ## make results AGG=<aggregate dir> [RUNS=<runs dir>] [KIT_VERSION=x.y.z], or RUNS=<runs dir> alone.
ifdef AGG
	python3 tools/build_results.py $(AGG) $(if $(RUNS),--runs-dir $(RUNS)) $(if $(KIT_VERSION),--kit-version $(KIT_VERSION))
else ifdef RUNS
	$(DEEPECG) aggregate --runs-dir $(RUNS) --output-dir .aggregate --on-duplicate error
	python3 tools/build_results.py .aggregate --runs-dir $(RUNS) $(if $(KIT_VERSION),--kit-version $(KIT_VERSION))
else
	@echo "usage: make results AGG=<aggregate dir> [RUNS=<runs dir>] [KIT_VERSION=x.y.z]"; \
	 echo "   or: make results RUNS=<runs dir> [KIT_VERSION=x.y.z]"; exit 2
endif
