from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
import os

# Database file, typically in project root or database container mount.
DB_FILE = os.environ.get("SQLITE_DB", "todo.db")  # fallback if not set

# SQLite Connection Utility
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ----------------- Pydantic Schemas -----------------
class TaskBase(BaseModel):
    title: str = Field(..., description="Title of the task", max_length=255)
    description: Optional[str] = Field("", description="Detailed description")
    completed: Optional[bool] = Field(False, description="Completion status")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    completed: Optional[bool]

class Task(TaskBase):
    id: int

# ------------------- DB Init ------------------------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.commit()

init_db()

# ----------------- FastAPI App ----------------------
app = FastAPI(
    title="Todo API",
    description="A simple FastAPI backend for a todo app.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Tasks", "description": "Task management endpoints"}
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", description="Check if backend is alive.")
def health_check():
    """Returns a simple health result."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.get("/tasks", response_model=List[Task], tags=["Tasks"], summary="List all tasks")
def list_tasks(db=Depends(get_db)):
    """Returns all todo tasks in the system."""
    cursor = db.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = [Task(**dict(row)) for row in cursor.fetchall()]
    return tasks

# PUBLIC_INTERFACE
@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, tags=["Tasks"], summary="Create a new task")
def create_task(task: TaskCreate, db=Depends(get_db)):
    """
    Create a new task.
    """
    cur = db.execute(
        "INSERT INTO tasks (title, description, completed) VALUES (?, ?, ?)",
        (task.title, task.description, int(task.completed))
    )
    db.commit()
    task_id = cur.lastrowid
    return Task(id=task_id, **task.dict())

# PUBLIC_INTERFACE
@app.get("/tasks/{id}", response_model=Task, tags=["Tasks"], summary="Get a specific task")
def get_task(id: int, db=Depends(get_db)):
    """
    Get a single task by ID.
    """
    cur = db.execute("SELECT * FROM tasks WHERE id=?", (id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**dict(row))

# PUBLIC_INTERFACE
@app.put("/tasks/{id}", response_model=Task, tags=["Tasks"], summary="Update entire task")
def update_task(id: int, task: TaskCreate, db=Depends(get_db)):
    """
    Update an entire task (title, description, completion).
    """
    cur = db.execute(
        "UPDATE tasks SET title=?, description=?, completed=? WHERE id=?",
        (task.title, task.description, int(task.completed), id)
    )
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return get_task(id, db)

# PUBLIC_INTERFACE
@app.patch("/tasks/{id}", response_model=Task, tags=["Tasks"], summary="Partial update (edit or toggle completion)")
def patch_task(id: int, updates: TaskUpdate, db=Depends(get_db)):
    """
    Partially update a task.
    """
    # Get current task
    cur = db.execute("SELECT * FROM tasks WHERE id=?", (id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    current = dict(row)
    # Merge updates
    updated = {
        "title": updates.title if updates.title is not None else current["title"],
        "description": updates.description if updates.description is not None else current["description"],
        "completed": int(updates.completed) if updates.completed is not None else current["completed"],
    }
    db.execute(
        "UPDATE tasks SET title=?, description=?, completed=? WHERE id=?",
        (updated["title"], updated["description"], updated["completed"], id)
    )
    db.commit()
    return get_task(id, db)

# PUBLIC_INTERFACE
@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], summary="Delete a task")
def delete_task(id: int, db=Depends(get_db)):
    """
    Delete a task by ID.
    """
    cur = db.execute("DELETE FROM tasks WHERE id=?", (id,))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return
