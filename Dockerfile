FROM python:3.12-slim

WORKDIR /app

# System libraries required by WeasyPrint (Pango, Cairo, GDK-Pixbuf, fonts).
# If these are unavailable/broken at build time, pdf_render.py falls back
# to a pure-Python reportlab renderer at runtime — the app still ships.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/data/uploads static/uploads

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
