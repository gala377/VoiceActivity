FROM python:3.8
RUN mkdir /app
WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml /app/

RUN poetry install -n

COPY voice_activity /app/voice_activity

CMD ["python", "-m", "voice_activity"]
