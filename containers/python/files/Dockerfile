# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install any needed packages specified in requirements.txt
RUN pip3 install -U pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Define environment variable
ENV FLASK_APP=python_executor.py

# Run the application with Waitress when the container launches
CMD ["waitress-serve", "--port=16000", "python_executor:app"]
