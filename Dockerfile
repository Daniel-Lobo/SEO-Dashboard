FROM python:3.10.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libmupdf-dev \
    pkg-config \
    python3-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    
# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY dashboard/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# Copy application code
COPY . .

# Setup start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
