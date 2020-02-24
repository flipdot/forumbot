FROM python:3.8-slim

RUN apt-get update && apt-get install -y locales pipenv git
# Set german locale
RUN echo "de_DE.UTF-8 UTF-8" >> /etc/locale.gen
ENV LANG de_DE.UTF-8
ENV LANGUAGE de_DE.UTF-8
ENV LC_ALL de_DE.UTF-8
RUN locale-gen de_DE.UTF-8

COPY Pipfile /app/
COPY Pipfile.lock /app/

WORKDIR  /app
RUN pipenv install

COPY src /app/src
COPY templates /app/templates

CMD pipenv run python src/app.py
