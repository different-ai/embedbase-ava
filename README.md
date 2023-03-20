<br />
<p align="center">

  <h1 align="center">Obsidian.md + <a href="https://github.com/different-ai/embedbase">Embedbase</a> =  Ava</h1>

  <p align="center">
    <a href="https://github.com/louis030195/obsidian-ava">Connect your Obsidian notes</a>
    ·
    <a href="https://github.com/different-ai/embedbase-ava/issues/new?assignees=&labels=enhancement">Request Feature</a>
    ·
    <a href="https://github.com/different-ai/embedbase-ava/issues/new?assignees=&labels=bug">Report Bug</a>
    <br />
  </p>
</p>

The codebase is under heavy development and the documentation is constantly evolving. Give it a try and let us know what you think by creating an issue. Watch [releases](https://github.com/different-ai/embedbase-ava/releases) of this repo to get notified of updates. And give us a star if you like it!


## Running locally

Follow the steps there to setup a supabase project:
https://docs.embedbase.xyz/self-hosting/deployment


```yaml
# config.yaml
openai_api_key: ...
openai_organization: ...
log_level: DEBUG
environment: development
vector_database: supabase
supabase_url: ...
supabase_key: ...
```

```bash
make run
```

### Infra

```bash
gcloud secrets create EMBEDBASE_AVA --replication-policy=automatic
gcloud secrets versions add EMBEDBASE_AVA --data-file=config.yaml
```

```bash
gcloud run services set-iam-policy embedbase-ava ./policy.yaml --region us-central1
```

### Automatic deployment through GitHub Actions

```bash
PROJECT_ID=$(gcloud config get-value project)

# create service account for pushing containers to gcr
# and deploying to cloud run
gcloud iam service-accounts create cloud-run-deployer \
  --display-name "Cloud Run deployer"

# Grant the appropriate Cloud Run role
# to the service account to provide repository access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:cloud-run-deployer@${PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/run.admin

# Grant the appropriate Cloud Storage role
# to the service account to provide registry access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:cloud-run-deployer@${PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/storage.admin

# Service Account User
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:cloud-run-deployer@${PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/iam.serviceAccountUser

# get svc key
KEY_PATH="obsidian-ai.cloud-run-deployer.svc.prod.json"
gcloud iam service-accounts keys create ${KEY_PATH} \
  --iam-account=cloud-run-deployer@${PROJECT_ID}.iam.gserviceaccount.com
cat ${KEY_PATH}
# copy the key to GitHub secrets as `GCP_SA_KEY_PROD`
rm -rf ${KEY_PATH}
```
