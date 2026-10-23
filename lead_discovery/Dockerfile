FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
WORKDIR /app
RUN groupadd -r vanguard && useradd -r -g vanguard -d /app -s /sbin/nologin vanguard
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN mkdir -p /app/data && chown -R vanguard:vanguard /app
USER vanguard
ENV PYTHONUNBUFFERED=1 PORT=8000 PLAYWRIGHT_HEADLESS=true ZERO_API_DISCOVERY_ENABLED=true
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
