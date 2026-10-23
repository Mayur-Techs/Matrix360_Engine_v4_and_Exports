FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
COPY matrix_engine/requirements.txt matrix_engine/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 matrix && mkdir -p /var/lib/matrix360 && chown -R matrix:matrix /app /var/lib/matrix360
USER matrix
ENV MATRIX_STORAGE_ROOT=/var/lib/matrix360
CMD ["sh", "-c", "uvicorn services.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
