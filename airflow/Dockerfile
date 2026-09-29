# Airflow image with our pipeline package installed, so DAG tasks can import it.
# Built from the repo root (see docker-compose.yml) so it can copy src/.
FROM apache/airflow:3.3.2-python3.12

# The official image expects pip to run as the "airflow" user, not root.
COPY --chown=airflow:0 pyproject.toml /opt/market_pipeline/
COPY --chown=airflow:0 src /opt/market_pipeline/src
RUN pip install --no-cache-dir /opt/market_pipeline
