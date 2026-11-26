FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd -g 10001 app && useradd -u 10001 -g app -M app
COPY pyproject.toml ./
COPY core ./core
COPY apps ./apps
COPY integrations ./integrations
COPY database ./database
RUN pip install --no-cache-dir ".[postgres]" && mkdir -p /app/data && chown app:app /app/data
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn","apps.api.main:app","--host","0.0.0.0","--port","8000"]
