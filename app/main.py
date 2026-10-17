from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import connect, init_db
from app.routers import auth, projects, tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    conn = connect()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="TaskFlow API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
