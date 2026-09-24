from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.inventory import router as inventory_router
from app.api.agent import router as agent_router
from app.api.sap import router as sap_router


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Automation system for BSP inventory reporting",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# INVENTORY ROUTER
# =========================================================

app.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Inventory"],
)


# =========================================================
# AGENT ROUTER
# =========================================================
#
# IMPORTANT:
#
# agent.py already contains:
#
#     router = APIRouter(prefix="/agent")
#
# Therefore DO NOT add prefix="/agent" here.
#
# Endpoint:
#
#     /agent/run
#
# =========================================================

app.include_router(
    agent_router,
    tags=["Agent"],
)


# =========================================================
# SAP ROUTER
# =========================================================
#
# IMPORTANT:
#
# sap.py already contains:
#
#     router = APIRouter(prefix="/sap")
#
# Therefore DO NOT add prefix="/sap" here.
#
# Endpoints will be:
#
#     /sap/attach
#     /sap/transaction
#     /sap/inspect-screen
#     /sap/set-text
#     /sap/press
#     /sap/select-combo
#     /sap/vkey
#
# =========================================================

app.include_router(
    sap_router,
    tags=["SAP"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "message": "BSP Inventory Automation API is running",
        "version": "1.0.0",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "SapAi Backend",
    }