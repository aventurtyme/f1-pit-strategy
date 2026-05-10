FROM python:3.11-slim

WORKDIR /app

# Install dependencies first — layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# uvicorn --reload for hot-reload during local development
# Remove --reload for any non-dev deployment
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]