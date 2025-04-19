# Use an official Python runtime as a parent image
FROM python:3.9-slim
# Or python:3.6-slim if you must stick to the older version

WORKDIR /usr/src/app

# Install necessary packages (if any beyond Python standard lib + requirements)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
# --no-cache-dir prevents caching which saves space
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Make port 80 available to the world outside this container (if needed, log-processor doesn't seem to expose one)
EXPOSE 80

# Define environment variables (will be overridden by K8s)
# ENV REDIS_HOST=redis-placeholder REDIS_PORT=6379 REDIS_CHANNEL=log_channel

# Run main.py when the container launches
CMD ["python3", "main.py"]