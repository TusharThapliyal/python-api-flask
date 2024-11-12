FROM python:3
COPY requirements.txt .
RUN apt update -y && pip install -r requirements.txt 
COPY app.py .
CMD ["python", "app.py"]
