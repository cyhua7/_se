from fastapi import FastAPI
import os
import psycopg2

app = FastAPI(root_path="/api")

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend inside Docker!"}

@app.get("/db-check")
def check_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME")
        )
        conn.close()
        return {"status": "success", "db": "Connected to PostgreSQL successfully!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}