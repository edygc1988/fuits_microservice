
import os
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_NAME = os.environ.get("DB_NAME", "fruitsdb")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

# Create table on startup
@app.on_event("startup")
def startup_event():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fruits (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100),
            descripcion TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


class Fruit(BaseModel):
    nombre: str
    descripcion: str

# Endpoint de health check para FastAPI
from datetime import datetime
from fastapi.responses import JSONResponse

@app.get("/health")
def health_check():
    return JSONResponse(content={
        "status": "healthy",
        "service": "fruits-api service",
        "timestamp": datetime.now().isoformat()
    })

@app.get("/fruits")
def get_fruits():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, descripcion FROM fruits;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "nombre": r[1], "descripcion": r[2]} for r in rows]

@app.post("/fruits")
def create_fruit(fruit: Fruit):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO fruits (nombre, descripcion) VALUES (%s, %s) RETURNING id;",
        (fruit.nombre, fruit.descripcion)
    )
    fruit_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": fruit_id, "message": "Fruit created"}
