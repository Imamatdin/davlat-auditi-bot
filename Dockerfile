FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

RUN mkdir -p /data
ENV DB_PATH=/data/davlat_auditi.db

EXPOSE 8080

CMD ["python", "-m", "bot.main"]
