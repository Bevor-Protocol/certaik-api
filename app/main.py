from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from .ai.routes import router as ai_router
from .blockchain.routes import router as blockchain_router
from .jobs import scheduler
from .status.routes import router as status_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # scheduler runs upon startup
    scheduler.start()
    yield
    print("shutting down")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/health")
async def health_check():
    return True


app.include_router(prefix="/blockchain", router=blockchain_router)
app.include_router(prefix="/ai", router=ai_router)
app.include_router(prefix="/status", router=status_router)
