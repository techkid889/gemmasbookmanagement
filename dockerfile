# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 6000 available to the world outside this container
EXPOSE 6000

# Define environment variable
ENV FLASK_APP=gemmasbookuploader.py

# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:6000", "gemmasbookuploader:app"]
CMD ["sh", "-c", "gunicorn gemmasbookuploader:app --bind 0.0.0.0:6000 --workers 4 & python -u booksdscan.py"]

