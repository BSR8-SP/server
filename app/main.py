from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import template, comment


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(template.router)
app.include_router(comment.router)