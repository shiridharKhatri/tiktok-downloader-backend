# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies for Chrome/Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    lsb-release \
    xdg-utils \
    --no-install-recommends

# Install Google Chrome for the Scraper Fallback
RUN curl -fSsL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor | tee /usr/share/keyrings/google-chrome.gpg > /dev/null \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application
COPY server/ .

# Expose the API port
EXPOSE 8087

# Start the application with high-concurrency uvicorn
# 4 workers is a good default for a standard VPS
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8087", "--workers", "4"]
