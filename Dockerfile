FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

COPY requirements-web.txt ./
RUN python -m pip install --no-cache-dir -r requirements-web.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /app --no-create-home app

COPY web_api.py THIRD_PARTY_NOTICES.md ./
COPY src/recommender/__init__.py \
     src/recommender/config.py \
     src/recommender/genre_recommender.py \
     src/recommender/als_recommender.py \
     src/recommender/poster_cache.py \
     src/recommender/poster_loader.py \
     src/recommender/tmdb_client.py ./src/recommender/
COPY assets/poster_placeholder.svg ./assets/
COPY scripts/15_install_demo_artifacts.py ./scripts/

# The checksum-pinned public release contains the catalog, ALS and built frontend.
# Supply TMDB_READ_ACCESS_TOKEN only as a runtime environment variable.
RUN python scripts/15_install_demo_artifacts.py --output-dir /app \
    && mkdir -p /app/artifacts/cache \
    && chown app:app /app/artifacts/cache

USER 10001:10001
VOLUME ["/app/artifacts/cache"]
EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8502/api/health', timeout=3).read()"

CMD ["python", "-m", "uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8502", "--workers", "1"]
