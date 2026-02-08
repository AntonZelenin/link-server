FROM python:3.12

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN mkdir "mess_user"
RUN mkdir "alembic"

COPY mess_user ./mess_user
COPY alembic ./alembic
COPY alembic.ini .

ENV ENVIRONMENT=production

EXPOSE 80

CMD ["uvicorn", "mess_user.main:app", "--host", "0.0.0.0", "--port", "80"]
