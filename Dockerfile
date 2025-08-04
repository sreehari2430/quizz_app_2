# Use an official Python runtime as the base image (slim version for smaller size)
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt first (for efficient caching during builds)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your Flask app runs on (default 5000)
EXPOSE 5000

# Set environment variables (if needed; override with .env or docker run flags)
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Command to run your app
CMD ["python", "run.py"]