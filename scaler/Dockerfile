# 1. Start from a lightweight Python base image
FROM python:3.9-slim

# 2. Set a working directory inside the container
WORKDIR /app

# 3. Copy the requirements file first
COPY requirements.txt .

# 4. Install the Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the scaler script into the container
COPY scaler.py .

# 6. Set the command to run when the container starts
CMD ["python", "scaler.py"]
