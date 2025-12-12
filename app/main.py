import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import JSONResponse
import time

app = FastAPI()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_NAME = os.environ.get("DB_NAME", "fruitsdb")

def get_conn():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME,
                connect_timeout=10
            )
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Intento {attempt + 1}/{max_retries} falló. Reintentando en {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"Error conectando a la base de datos: {e}")
                raise

# IMPORTANTE: El evento startup DEBE estar antes que las rutas
@app.on_event("startup")
async def startup_event():
    print(f"🚀 Iniciando API - Conectando a PostgreSQL en {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
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
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error en startup: {e}")
        # No hacer raise aquí para que la API siga funcionando
        print("⚠️ La API continuará pero puede tener problemas de DB")

class Fruit(BaseModel):
    nombre: str
    descripcion: str

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Fruits API is running", "version": "1.0"}

@app.get("/health")
async def health_check():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        
        return {
            "status": "healthy",
            "service": "fruits-api",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "fruits-api",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/fruits")
async def get_fruits():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, descripcion FROM fruits ORDER BY id;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "nombre": r[1], "descripcion": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/fruits")
async def create_fruit(fruit: Fruit):
    try:
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
        return {"id": fruit_id, "nombre": fruit.nombre, "message": "Fruit created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/fruits/{fruit_id}")
async def delete_fruit(fruit_id: int):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM fruits WHERE id = %s RETURNING id;", (fruit_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted:
            return {"message": f"Fruit {fruit_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Fruit {fruit_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")