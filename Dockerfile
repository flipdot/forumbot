FROM python:3.13-slim

RUN apt-get update && apt-get install -y locales git
# Set german locale
RUN echo "de_DE.UTF-8 UTF-8" >> /etc/locale.gen
ENV LANG de_DE.UTF-8
ENV LANGUAGE de_DE.UTF-8
ENV LC_ALL de_DE.UTF-8
RUN locale-gen de_DE.UTF-8

RUN pip install poetry==1.8.4

COPY pyproject.toml /app/
COPY poetry.lock /app/

WORKDIR  /app
RUN poetry install

COPY src /app/src
COPY templates /app/templates

ENTRYPOINT ["poetry", "run"]
CMD python src/app.py
