FROM python:3.12.10
LABEL authors="OldestSalt"

WORKDIR /bot

COPY requirements.txt .

RUN apt-get update
RUN pip3 install --no-cache-dir -r --no-deps requirements.txt

COPY . .

ENTRYPOINT ["python3", "main.py"]