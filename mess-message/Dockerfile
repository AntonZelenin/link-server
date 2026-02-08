FROM python:3.12

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN mkdir "mess_message"
RUN mkdir "alembic"

COPY mess_message ./mess_message
COPY alembic ./alembic
COPY alembic.ini .

ENV ENVIRONMENT=production

EXPOSE 80

CMD ["uvicorn", "mess_message.main:app", "--host", "0.0.0.0", "--port", "80"]
