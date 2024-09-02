FROM python:3.12-slim-bookworm

WORKDIR /code
COPY requirements.txt /code
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT [ "python3", "main.py" ]
