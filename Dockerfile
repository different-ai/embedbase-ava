FROM ghcr.io/different-ai/embedbase:0.8.8-minimal
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y git && apt-get clean && \
    pip install -r requirements.txt && rm requirements.txt
COPY ./middlewares/history/history.py /app/middlewares/history/history.py
COPY main.py main.py
COPY docker-entrypoint.sh docker/docker-entrypoint.sh

ENTRYPOINT ["docker/docker-entrypoint.sh"]
CMD ["embedbase"]