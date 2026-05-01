from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3
import uuid

app = FastAPI()

DB = "saas.db"

# ================= DB =================
def db():
    return sqlite3.connect(DB)

def init():
    conn = db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            hwid TEXT,
            expires TEXT,
            active INTEGER
        )
    """)
    conn.commit()
    conn.close()

init()

# ================= MODELOS =================
class Create(BaseModel):
    days: int = 0

class Validate(BaseModel):
    key: str
    hwid: str

# ================= HOME =================
@app.get("/")
def home():
    return {"status": "SAAS ONLINE 🚀"}

# ================= CREATE KEY =================
@app.post("/create")
def create(data: Create):
    key = str(uuid.uuid4())

    expires = None
    if data.days > 0:
        expires = (datetime.utcnow() + timedelta(days=data.days)).isoformat()

    conn = db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO licenses VALUES (?, '', ?, 1)",
        (key, expires)
    )

    conn.commit()
    conn.close()

    return {"key": key}

# ================= VALIDATE =================
@app.post("/validate")
def validate(data: Validate):
    conn = db()
    c = conn.cursor()

    c.execute("SELECT hwid, expires, active FROM licenses WHERE key=?", (data.key,))
    row = c.fetchone()

    if not row:
        return {"status": "invalid"}

    hwid_db, expires, active = row

    if active == 0:
        return {"status": "blocked"}

    if expires and datetime.utcnow() > datetime.fromisoformat(expires):
        return {"status": "expired"}

    # 🔒 TRAVA NO PRIMEIRO PC
    if hwid_db == "":
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (data.hwid, data.key))
        conn.commit()
        conn.close()
        return {"status": "ok"}

    # ❌ OUTRO PC
    if hwid_db != data.hwid:
        conn.close()
        return {"status": "wrong_device"}

    conn.close()
    return {"status": "ok"}