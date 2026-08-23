FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements-ai.txt

# Chroma 인덱스와 동일한 768차원 임베딩 모델을 이미지에 고정한다.
# 런타임마다 모델을 다시 내려받지 않아 Railway 재배포가 안정적이다.
ENV HF_HOME=/opt/huggingface \
    EMBEDDING_LOCAL_FILES_ONLY=true
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"

COPY app ./app
COPY data ./data
COPY scripts ./scripts
COPY main.py ./

EXPOSE 8000

CMD ["sh", "-c", "python -m scripts.verify_chroma && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
