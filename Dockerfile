# Базовый образ с Python
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь проект внутрь контейнера
COPY . .

# Открываем порт (если ты планируешь Flask-интерфейс)
EXPOSE 5000

# Точка входа
CMD ["python", "main.py"]
