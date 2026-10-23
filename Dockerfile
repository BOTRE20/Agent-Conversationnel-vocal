FROM python:3.11-bullseye

RUN apt-get update && \
    apt-get install -y \
        gcc \
        g++ \
        make \
        pkg-config \
        portaudio19-dev \
        ffmpeg \
        libasound2-dev \
        libjack-dev \
        libgtk-3-dev \
        libwebkit2gtk-4.0-dev \
        libffi-dev \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
