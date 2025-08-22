# Use Debian slim; has chromium & chromedriver packages
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Chromium & Chromedriver + basic deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg unzip \
    chromium chromium-driver libnss3 libxss1 libgbm1 libasound2 fonts-liberation xdg-utils \
 && rm -rf /var/lib/apt/lists/*

# Helpful envs for Selenium/Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER=/usr/bin/chromedriver
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command: run your script
CMD ["python", "main.py"]
