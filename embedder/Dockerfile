FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

LABEL authors="OldestSalt"

WORKDIR /embedder

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y --no-install-recommends python3.12.10 python3.12.10-distutils python3.12.10-venv
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12.10 1 \
 && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12.10 1
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python
RUN pip3 install --no-cache-dir --no-deps -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "main.py"]