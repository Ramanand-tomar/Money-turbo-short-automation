# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONPATH="/MoneyPrinterTurbo"
ENV PYTHONUNBUFFERED=1
ENV PORT=8085

# Set the working directory in the container
WORKDIR /MoneyPrinterTurbo

# Install system dependencies (git, FFmpeg, ImageMagick)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Fix security policy for ImageMagick to allow moviepy text clips
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml

# Copy requirements file and install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the workspace files (including config.toml and resource/public with React build)
COPY . .

# Set /MoneyPrinterTurbo directory permissions
RUN chmod 777 /MoneyPrinterTurbo

# Expose port (overridden dynamically by Render at runtime)
EXPOSE 8085

# Command to run the FastAPI server (serves the backend AND the React frontend)
CMD ["python", "main.py"]