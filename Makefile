LATEST_IMAGE_URL="ghcr.io/another-ai/embedbase:latest"
VERSION="0.0.1"
IMAGE_URL="ghcr.io/another-ai/embedbase:${VERSION}"
LOCAL_PORT="8000"

-include .env

install: ## [DEVELOPMENT] Install the API dependencies
	virtualenv env; \
	source env/bin/activate; \
	pip install -r requirements.txt; \
	pip install -r requirements-test.txt
	@echo "Done, run '\033[0;31msource env/bin/activate\033[0m' to activate the virtual environment"

run/dev: ## [Local development] Run the development docker image.
	docker-compose up

run/prod:
	docker-compose up -f docker-compose-prod.yaml

test: ## [Local development] Run tests with pytest.
# TODO: start docker embedbase here
	python3 -m pytest -s middlewares/history/test_history.py
	@echo "Done testing"

release: ## [Local development] Release a new version of the API.
	echo "Releasing version ${VERSION}"; \
	read -p "Commit content:" COMMIT; \
	git add .; \
	echo "Committing '${VERSION}: $$COMMIT'"; \
	git commit -m "${VERSION}: $$COMMIT"; \
	git push origin main; \
	git tag ${VERSION}; \
	git push origin ${VERSION}
	@echo "Done, check https://github.com/another-ai/embedbase/actions"

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'