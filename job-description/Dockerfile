# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy project files into the container
COPY . .

RUN pip install -r requirements.txt

RUN pip install spacy
RUN python -m spacy download en_core_web_lg  # 👈 Critical addition
# Expose the port your app runs on
EXPOSE 3002

# Start the Flask app
CMD ["python", "job.py"]
