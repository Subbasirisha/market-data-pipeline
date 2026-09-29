# Airflow image with our pipeline package installed, so DAG tasks can import it.
# Built from the repo root (see docker-compose.yml) so it can copy src/.
FROM apache/airflow:3.3.2-python3.12

# dbt gets its own virtualenv: dbt and Airflow both pin many shared libraries, and
# installing them together tends to break one or the other. Tasks call /opt/dbt-venv/bin/dbt.
# The image runs as the non-root "airflow" user, which can't create folders in /opt:
# create it as root, hand it over, and switch straight back.
USER root
RUN mkdir /opt/dbt-venv && chown airflow:0 /opt/dbt-venv
USER airflow
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir "dbt-postgres>=1.11"

# The official image expects pip to run as the "airflow" user, not root.
COPY --chown=airflow:0 pyproject.toml /opt/market_pipeline/
COPY --chown=airflow:0 src /opt/market_pipeline/src
RUN pip install --no-cache-dir /opt/market_pipeline
