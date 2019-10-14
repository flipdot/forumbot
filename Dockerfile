FROM python:3.7

# Set german locale
RUN apt-get update && apt-get install -y locales
RUN echo "de_DE.UTF-8 UTF-8" >> /etc/locale.gen
ENV LANG de_DE.UTF-8
ENV LANGUAGE de_DE.UTF-8
ENV LC_ALL de_DE.UTF-8
RUN locale-gen de_DE.UTF-8

COPY requirements.txt /app/

WORKDIR  /app
RUN pip install -r requirements.txt
RUN pip install nose

COPY src /app/src
COPY templates /app/templates

RUN nosetests tests

CMD python src/app.py