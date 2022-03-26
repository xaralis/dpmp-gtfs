FROM python:3.10-slim-bullseye

RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/bin/poetry && \
    poetry --version

COPY . /opt/app

WORKDIR /opt/app

RUN poetry install

CMD ["poetry", "run"]
