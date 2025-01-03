FROM python:3.9-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8000

# Run the application
CMD ["poetry", "run" ,"uvicorn", "app.main:app" ,"--host", "0.0.0.0" ,"--port", "8000"]