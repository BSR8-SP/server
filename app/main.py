from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import template, comment, rating, maps
from app.services.sptrans import sptrans_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await sptrans_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(template.router)
app.include_router(comment.router)
app.include_router(rating.router)
app.include_router(maps.router)
