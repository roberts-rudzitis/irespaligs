FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_ROOT=/srv/staticfiles

# gettext: needed for makemessages / compilemessages (translations)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dev dependencies (pytest) are installed too; set INSTALL_DEV=0 for a smaller production image.
ARG INSTALL_DEV=1
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$INSTALL_DEV" = "1" ]; then pip install -r requirements-dev.txt; else pip install -r requirements.txt; fi

COPY . .

RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "irespaligs.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
