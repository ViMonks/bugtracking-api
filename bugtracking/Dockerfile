FROM python:3.8-slim

# set environment variables
ENV APP_HOME /app
WORKDIR $APP_HOME
ENV PORT 8080
# the two below ensure that print statements and log messages appear in Cloud Logging
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# installing dependencies
COPY ./requirements /requirements
RUN pip install -r /requirements/production.txt

# copying local code to container image
COPY ./manage.py ./manage.py
COPY ./config ./config
COPY ./bugtracking ./bugtracking

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind=0.0.0.0:$PORT --workers=1 --threads=8 --timeout=0 --log-level=debug config.wsgi:application

# move this to root directory when ready to build
