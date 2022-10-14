FROM python:3.8.5

RUN mkdir /src
WORKDIR /src
COPY ./requirements.txt /scripts/
RUN pip3 install --upgrade pip
RUN pip3 install -r /scripts/requirements.txt