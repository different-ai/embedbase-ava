from typing import Tuple
from fastapi import FastAPI, Request

def middleware(app: FastAPI):
    @app.middleware("http")
    async def history(request: Request, call_next) -> Tuple[str, str]:
        print("history before")
        response = await call_next(request)
        print("history after")
        return response