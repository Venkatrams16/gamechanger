FROM python:3.10.8-slim-buster

# Install system dependencies
RUN apt-get update \
    && apt-get install -y gcc python3-dev \
    && apt-get clean

# Copy requirements file
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip3 install -U pip \
    && pip3 install -U -r /requirements.txt

# Set up your application directory
RUN mkdir /gamechanger
WORKDIR /gamechanger

# Copy your application code
COPY start.sh /gamechanger/start.sh

# Set permissions for start.sh if needed
RUN chmod +x /gamechanger/start.sh

# Define the command to run your application
CMD ["/bin/bash", "/gamechanger/start.sh"]
