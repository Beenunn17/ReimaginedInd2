# Use the original, working Python runtime
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies AND the Playwright browser dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

# Copy the rest of the application's code into the container
COPY . .

# Create the data files inside the container
RUN python create_dummy_data.py

# Expose the port the container will listen on. 
# This is documentation for the user, Cloud Run uses the PORT env var.
EXPOSE 8000

# Set the command to run the application.
# This uses the PORT environment variable provided by Cloud Run.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}