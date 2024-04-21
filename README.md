# Swift shopw Gen AI fast api

## Requirements

You'll must have installed:

- [Python 3.6+](https://www.python.org/downloads/)
- [Virtual Environments with Python3.6+](https://docs.python.org/3/tutorial/venv.html)
- [Docker](https://docs.docker.com/engine/install/)
- [Docker-compose](https://docs.docker.com/compose/install/)

___

## Setup Project

Create virtual environment

```bash
python -m venv venv
```

Activating created virtual environment

```bash
source venv/bin/activate 

```

Git bash on windows

```bash
source venv/Scripts/activate 
```

Install app dependencies

```bash
pip install -r requirements.txt

```

Run application

```bash
uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-5000} --reload
```

___

## Running Application

Starting database (postgres:alpine3.14)

```bash
docker-compose up -d
```

## Rebuilding docker image

```bash
docker build . -t prajinults/swift-shop-gen-ai-fr
docker tag prajinults/swift-shop-gen-ai-fr  prajinults/swift-shop-gen-ai-fr:v2.5.0
docker push prajinults/swift-shop-gen-ai-fr
docker push prajinults/swift-shop-gen-ai-fr:v2.5.0

docker run -d -p 8080:8080 prajinults/swift-shop-gen-ai-fr

```
