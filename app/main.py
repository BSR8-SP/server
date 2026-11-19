import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import template, comment, rating, maps, statistics

from app.services.gtfs import gtfs
from app.services.sptrans import sptrans_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Downloads the GTFS when GTFS_URL is set and the files are missing.
    await asyncio.to_thread(gtfs.download_if_missing)
    yield
    await sptrans_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(template.router)
app.include_router(comment.router)
app.include_router(rating.router)
app.include_router(maps.router)
app.include_router(statistics.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
