FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (JavaScript runtime for yt-dlp)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Verify Deno installation
RUN deno --version

# Install Python dependencies - force reinstall yt-dlp
COPY requirements.txt .
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt
RUN pip install --no-cache-dir --force-reinstall yt-dlp==2024.12.13

# Copy application code
COPY . .

# Create download directory
RUN mkdir -p /opt/render/project/src/downloads

# Expose port
EXPOSE 10000

# Run the app
CMD ["python", "app.py"]