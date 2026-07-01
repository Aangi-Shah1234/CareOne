FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CAREONE_HOST=0.0.0.0
ENV PORT=8501
ENV CAREONE_PORT=8501
ENV CAREONE_LIVE_LLM=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8501"]
