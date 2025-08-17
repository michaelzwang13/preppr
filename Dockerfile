FROM python:3.12-slim

# Install OS packages needed for MySQL + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential default-libmysqlclient-dev curl && \
  rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose the App Runner port
EXPOSE 8080

# Start the Flask app using gunicorn
# If create_app() is in src/__init__.py:
CMD ["gunicorn", "-w", "3", "-k", "gthread", "-b", "0.0.0.0:8080", "src:create_app()"]