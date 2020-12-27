FROM python:3.8
RUN mkdir /app
RUN mkdir /data
WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml /app/

RUN poetry install -n

COPY voice_activity /app/voice_activity
COPY .env .env
CMD ["python", "-m", "voice_activity"]
