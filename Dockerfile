FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000"]
