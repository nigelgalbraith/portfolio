FROM python:3.12-alpine
RUN apk add --no-cache postgresql-client

WORKDIR /app/src

COPY api/requirements.txt /app/src/
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ /app/src/

EXPOSE 5000

CMD ["python", "app.py"]
