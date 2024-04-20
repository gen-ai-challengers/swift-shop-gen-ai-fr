# This is a sample Dockerfile you can modify to deploy your own app based on face_recognition

FROM python:3.12.3-slim

RUN apt-get -y update
RUN apt-get install -y --fix-missing \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean && rm -rf /tmp/* /var/tmp/*


COPY requirements.txt /code/requirements.txt
WORKDIR /code
RUN pip install -r requirements.txt
COPY app /code/app/
COPY public /code/public/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

