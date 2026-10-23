from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3
import re
from datetime import datetime, timezone

app = FastAPI(title="Celestius Event Registration API")

DATABASE = "registrations.db"
CAPACITY = 50


# Create the database and table
def create_database():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                college_department TEXT,
                registered_at TEXT NOT NULL
            )
        """)


create_database()


# Student details received from the API
class Student(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    college_department: Optional[str] = Field(
        default=None, max_length=150
    )


# Welcome endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Celestius Backend API!"}


# Register a student
@app.post("/register", status_code=201)
def register_student(student: Student):
    name = student.name.strip()
    email = student.email.strip().lower()
    department = student.college_department

    if not name:
        raise HTTPException(400, "Name cannot be empty")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Invalid email address")

    if department is not None:
        department = department.strip() or None

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            "SELECT id FROM registrations WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            raise HTTPException(409, "Email already registered")

        count = conn.execute(
            "SELECT COUNT(*) FROM registrations"
        ).fetchone()[0]

        if count >= CAPACITY:
            raise HTTPException(409, "Event is full")

        registered_at = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute(
            """INSERT INTO registrations
               (name, email, college_department, registered_at)
               VALUES (?, ?, ?, ?)""",
            (name, email, department, registered_at)
        )

        registration_id = cursor.lastrowid

        result = conn.execute(
            "SELECT * FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()

    return {
        "message": "Registration successful",
        "registration": {
            "id": result[0],
            "name": result[1],
            "email": result[2],
            "college_department": result[3],
            "registered_at": result[4]
        }
    }


# View all registrations
@app.get("/registrations")
def get_registrations():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM registrations ORDER BY id"
        ).fetchall()

    return {
        "total": len(rows),
        "capacity": CAPACITY,
        "registrations": [dict(row) for row in rows]
    }


# View one registration by ID
@app.get("/registrations/{registration_id}")
def get_registration(registration_id: int):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Registration not found")

    return dict(row)