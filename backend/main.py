from __future__ import annotations

import os
from typing import Optional, Any, Literal

import httpx
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# =========================
# Config
# =========================
ESP_BASE_URL = os.getenv("ESP_BASE_URL").rstrip("/")

# If you enable USE_BASIC_AUTH=1 on the ESP, set these env vars:
ESP_USER = os.getenv("ESP_USER", "")
ESP_PASS = os.getenv("ESP_PASS", "")


def _esp_auth() -> Optional[httpx.BasicAuth]:
    if ESP_USER and ESP_PASS:
        return httpx.BasicAuth(ESP_USER, ESP_PASS)
    return None


# =========================
# Models
# =========================
class EspState(BaseModel):
    up: bool
    down: bool


class RelayTarget(BaseModel):
    relay: Literal["up", "down", "both"] = "both"


class ProxyResponse(BaseModel):
    ok: bool
    esp_response: Any


# =========================
# Helpers
# =========================
async def esp_get_json(path: str) -> Any:
    url = f"{ESP_BASE_URL}{path}"
    print("GET from ESP URL:", url)
    attempts = 3  # initial try + 2 retries
    for attempt in range(1, attempts + 1):
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, auth=_esp_auth(), timeout=5.0)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                if attempt >= attempts:
                    raise HTTPException(status_code=502, detail=f"ESP error: {str(e)}") from e
                # wait before retrying
                await asyncio.sleep(3)


async def esp_post_json(path: str, params: Optional[dict] = None) -> Any:
    url = f"{ESP_BASE_URL}{path}"
    print("POST to ESP URL:", url, "with params:", params)
    attempts = 3
    for attempt in range(1, attempts + 1):
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, params=params, auth=_esp_auth(), timeout=5.0)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                if attempt >= attempts:
                    raise HTTPException(status_code=502, detail=f"ESP error: {str(e)}") from e
                await asyncio.sleep(3)


# =========================
# API
# =========================
app = FastAPI(title="ESP Relay Proxy API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

# allow your Vite dev server origin(s)
# Read `WEB_ORIGINS` from environment as a comma-separated list, e.g.
origins_env = os.getenv("WEB_ORIGINS")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         # or ["*"] for quick dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    # Backend + ESP reachability
    print("Base URL:", ESP_BASE_URL)
    esp = await esp_get_json("/health")
    return {"ok": True, "esp_base_url": ESP_BASE_URL, "esp": esp}


@app.get("/state", response_model=EspState)
async def state():
    data = await esp_get_json("/state")
    return EspState(up=bool(data.get("up")), down=bool(data.get("down")))


# ---- Independent relay control (matches your ESP behavior) ----
@app.post("/up/on", response_model=ProxyResponse)
async def up_on():
    # ESP: POST /up (turns UP on, does not touch DOWN)
    resp = await esp_post_json("/up")
    return ProxyResponse(ok=True, esp_response=resp)


@app.post("/down/on", response_model=ProxyResponse)
async def down_on():
    # ESP: POST /down (turns DOWN on, does not touch UP)
    resp = await esp_post_json("/down")
    return ProxyResponse(ok=True, esp_response=resp)


@app.post("/up/off", response_model=ProxyResponse)
async def up_off():
    # ESP: POST /stop?relay=up
    resp = await esp_post_json("/stop", params={"relay": "up"})
    return ProxyResponse(ok=True, esp_response=resp)


@app.post("/down/off", response_model=ProxyResponse)
async def down_off():
    # ESP: POST /stop?relay=down
    resp = await esp_post_json("/stop", params={"relay": "down"})
    return ProxyResponse(ok=True, esp_response=resp)


@app.post("/stop", response_model=ProxyResponse)
async def stop(body: RelayTarget):
    # stop up/down/both
    params = {"relay": body.relay} if body.relay else None
    resp = await esp_post_json("/stop", params=params)
    return ProxyResponse(ok=True, esp_response=resp)
