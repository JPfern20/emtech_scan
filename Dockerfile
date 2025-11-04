# Use an official slim Python image
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install required system packages (gocr, cuneiform, poppler for pdf2image, tk for GUI if you want)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gocr \
    cuneiform \
    poppler-utils \
    libgl1-mesa-glx \
    tcl8.6 \
    tk8.6 \
    python3-tk \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install into the image
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY emtechscan.py /app/emtechscan.py

# Default working dir (mounted at runtime)
ENTRYPOINT ["python3", "/app/emtechscan.py"]