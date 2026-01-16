FROM python:3.12.10
LABEL authors="OldestSalt"

WORKDIR /db_manager

COPY requirements.txt .

RUN apt-get update
RUN pip3 install --no-cache-dir --no-deps -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "main.py"]