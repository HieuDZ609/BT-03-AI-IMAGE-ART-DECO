FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY telegram_notify.py .
EXPOSE 8089
CMD ["python", "telegram_notify.py"]