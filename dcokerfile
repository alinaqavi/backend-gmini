# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependencies first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the Flask app
CMD ["python", "app.py"]
