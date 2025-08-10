FROM python:3.11-slim

# Browser worker container for optional SEO scraping using Playwright
WORKDIR /app

# Install browser-specific dependencies (Playwright and BeautifulSoup)
COPY requirements.browser.txt ./
RUN pip install --no-cache-dir -r requirements.browser.txt \
    && playwright install --with-deps chromium

# Copy the worker code into the container
COPY . .

# Default command launches the placeholder SEO worker
CMD ["python", "-m", "workers.seo_worker"]