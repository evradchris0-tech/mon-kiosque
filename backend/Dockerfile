FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY prompts ../prompts
EXPOSE 8000
CMD ["uvicorn", "app.api.main:creer_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
