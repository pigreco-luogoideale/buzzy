FROM python:3.7-alpine

WORKDIR /app

RUN apk add --no-cache build-base
ADD requirements.txt /app
RUN pip3 install -r requirements.txt
ADD . /app

CMD uvicorn --host=0.0.0.0 --port=80 buzzy.main:app
