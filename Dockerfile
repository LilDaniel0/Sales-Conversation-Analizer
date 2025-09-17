FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libopus0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Sales-Conversation-Analizer

COPY pyproject.toml .

RUN pip install --no-cache-dir uv
RUN uv sync

COPY . .

RUN mkdir -p /data/logs

EXPOSE 5000

ENV DEBUG=False
ENV PORT=5000
ENV LOG_FILE=/data/logs/logs.txt

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port", "5000", "--server.address", "0.0.0.0"]