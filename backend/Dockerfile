FROM python:3.12-bookworm AS build

WORKDIR /code
COPY requirements.txt /code
RUN pip3 install -r requirements.txt

CMD [ "/bin/bash" ]

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get -qq -y install libmariadb-dev

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY . .

CMD [ "python3", "main.py" ]

