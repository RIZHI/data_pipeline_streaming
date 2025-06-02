# Dockerfile
FROM python:3.10-slim

# Install Java for PySpark
RUN apt-get update && apt-get install -y openjdk-11-jdk curl && apt-get clean

# Set environment variables for Java
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
WORKDIR /app
COPY simulate_producer.py .
COPY pyspark_streaming_aggregator.py .

CMD ["bash"]
