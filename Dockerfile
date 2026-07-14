FROM python:3.11-slim

# Instala ffmpeg direto no container
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

RUN mkdir -p uploads outputs

EXPOSE 8080

CMD ["python", "server.py"]
