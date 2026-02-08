FROM python:3.12

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN mkdir "mess_auth"
RUN mkdir "alembic"

COPY mess_auth ./mess_auth
COPY alembic ./alembic
COPY alembic.ini .

ENV ENVIRONMENT=production

EXPOSE 80

CMD ["uvicorn", "mess_auth.main:app", "--host", "0.0.0.0", "--port", "80"]
