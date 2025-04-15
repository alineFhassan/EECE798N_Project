# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# Copy the application code
COPY app.py .

# Expose the port
EXPOSE 5003

# Command to run the application
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5003"]