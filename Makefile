LOCAL_PORT="8000"
SERVICE="embedbase-internal"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null || echo "none")
LATEST_IMAGE_URL=$(shell echo "gcr.io/${GCLOUD_PROJECT}/${SERVICE}:latest")
VERSION=$(shell sed -n 's/.*image:.*:\(.*\)/\1/p' service.prod.yaml)
IMAGE_URL=$(shell echo "gcr.io/${GCLOUD_PROJECT}/${SERVICE}:${VERSION}")
REGION="us-central1"

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
	docker-compose -f docker-compose-prod.yaml up

test: ## [Local development] Run tests with pytest.
# TODO: start docker embedbase here
	python3 -m pytest -s middlewares/history/test_history.py
	@echo "Done testing"

build: ## [Local development] Build the docker image.
	@echo "Building docker image for urls ${LATEST_IMAGE_URL} and ${IMAGE_URL}"
	docker buildx build . --platform linux/amd64 -t ${LATEST_IMAGE_URL} -f ./Dockerfile
	docker buildx build . --platform linux/amd64 -t ${IMAGE_URL} -f ./Dockerfile

push: build ## [Local development] Push the docker image to GCP.
	docker push ${IMAGE_URL}
	docker push ${LATEST_IMAGE_URL}

deploy: push ## [Local development] Deploy the Cloud run service.
	@echo "Will deploy embedbase-internal to ${REGION} on ${GCLOUD_PROJECT}"
	gcloud beta run services replace ./service.prod.yaml --region ${REGION}

release: ## [Local development] Release a new version of the API.
	echo "Releasing version ${VERSION}"; \
	read -p "Commit content:" COMMIT; \
	git add .; \
	echo "Committing '${VERSION}: $$COMMIT'"; \
	git commit -m "${VERSION}: $$COMMIT"; \
	git push origin main; \
	git tag ${VERSION}; \
	git push origin ${VERSION}
	@echo "Done, check https://github.com/another-ai/embedbase-internal/actions"

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'