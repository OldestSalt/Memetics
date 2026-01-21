FROM python:3.12.10

LABEL authors="OldestSalt"

WORKDIR /embedder

RUN apt-get update

COPY requirements.txt .

RUN pip3 install --no-cache-dir --no-deps -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "main.py"]