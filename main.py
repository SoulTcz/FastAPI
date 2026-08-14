# app/main.py
# Ab main.py sirf "app ka entry point" hai — saara logic alag files me hai

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import startup_db_client, shutdown_db_client
from app.api.v1.users import router as users_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin_products import router as admin_products_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_db_client(app)
    yield
    await shutdown_db_client(app)


app = FastAPI(lifespan=lifespan, title="Baking E-commerce Backend")

# CORS - frontend se requests allow karne ke liye (Week 1 deliverable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # production me specific domain daalna
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (Week 1 deliverable)
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Baking E-commerce API is running"}


# Router include - ab yeh sab /api/v1/... prefix ke saath kaam karega
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_products_router)
