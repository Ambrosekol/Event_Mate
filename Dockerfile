FROM python:3

COPY requirements.txt /Eventmate/
COPY backend /Eventmate/backend/

WORKDIR /Eventmate

RUN pip install -r requirements.txt

CMD [ "python3", "backend/app.py"]
