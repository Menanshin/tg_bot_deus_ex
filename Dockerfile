FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости отдельным слоем — пересобирается только при их изменении.
# build-essential не нужен: все пакеты ставятся из wheel-ов.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY main.py .

# Состояние (whitelist, статистика) переживает передеплой только на volume:
#   docker run -v bot_state:/data -e STATE_DIR=/data ...
ENV STATE_DIR=/data
RUN mkdir -p /data && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=4).status==200 else 1)"

# workers=1 обязательно: состояние живёт в памяти процесса, на нескольких
# воркерах whitelist и статистика разъедутся. Параллелизм даёт threads.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", \
     "--access-logfile", "-", "--timeout", "60", "main:app"]
