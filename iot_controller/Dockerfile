FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt requirements.txt
COPY main.py main.py

RUN pip install -r requirements.txt

ENTRYPOINT ["python3", "-u", "main.py"]
