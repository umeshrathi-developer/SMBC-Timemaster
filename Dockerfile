FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DATA_DIR=/app/data \
    LOG_DIR=/app/logs \
    MEDIA_ROOT=/app/media

WORKDIR /app

RUN addgroup --system timemaster && adduser --system --ingroup timemaster timemaster

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN mkdir -p /app/data /app/logs /app/media /app/staticfiles \
    && chown -R timemaster:timemaster /app

USER timemaster

RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
CMD ["gunicorn", "timemaster_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
