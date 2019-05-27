FROM python:3.7-alpine

RUN apk add --no-cache build-base
ADD . /app
WORKDIR /app
RUN pip3 install -r requirements.txt

CMD uvicorn --host=0.0.0.0 --port=80 buzzy.main:app
