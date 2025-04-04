FROM python:3.11-slim

WORKDIR /app

COPY tg_bot /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
