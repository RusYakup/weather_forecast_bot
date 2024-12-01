# Этап 1: Сборка зависимостей
FROM python:3.11-alpine AS builder

WORKDIR /app
COPY . /app
#COPY ../.env /.env
RUN pip install --timeout=120 pipenv
RUN pipenv install

#CMD ["python", "-m", "src.app"]
