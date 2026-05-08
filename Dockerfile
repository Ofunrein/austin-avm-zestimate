FROM python:3.13-slim

WORKDIR /app

# copy ML source (needed for feature engineering imports)
COPY ml/src/ ./ml/src/

# copy API
COPY api/ ./api/

# install system deps for lightgbm on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r api/requirements.txt

# HuggingFace Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
