FROM python:3.11-slim

WORKDIR /app

COPY be/ .

ENV BE_PORT=9000

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
