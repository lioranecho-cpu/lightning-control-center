FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port
EXPOSE 8765

# Start LCC
CMD ["uvicorn", "lcc_api:app", "--host", "0.0.0.0", "--port", "8765"]
