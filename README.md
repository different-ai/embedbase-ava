

```yaml
# config.yaml
# ...
middlewares:
  - middlewares.history
# ...
```

```bash
gcloud secrets create EMBEDBASE_INTERNAL --replication-policy=automatic
gcloud secrets versions add EMBEDBASE_INTERNAL --data-file=config.yaml
```
