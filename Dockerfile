# Repository B - Builder: Package Python, the dataset, and tests without dependencies.
FROM python:3.12-slim
WORKDIR /app
COPY main.py .
COPY data/ data/
COPY tests/ tests/
# Repository B - Builder: Start the interactive application only at runtime.
CMD ["python", "main.py"]
