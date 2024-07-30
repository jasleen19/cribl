FROM python:3.12-slim
RUN pip install "poetry==1.8.3" "poethepoet==0.27.0"
WORKDIR /project
COPY pyproject.toml poetry.lock main.py ./
COPY ./app ./app
RUN poetry install --no-dev
CMD ["poe", "run"]
