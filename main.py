from embedbase import get_app

from embedbase.settings import get_settings
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from middlewares.history.history import PRODUCTION_IGNORED_PATHS, DetailedError, History
from embedbase.supabase_db import Supabase
import semantic_version
import logging

settings = get_settings()


async def version_check(request: Request, call_next):
    if any(path in request.scope["path"] for path in PRODUCTION_IGNORED_PATHS):
        return await call_next(request)

    # if X-Client-Version < 2.18.7 deny
    # extract version from header
    for name, value in request.scope["headers"]:  # type: bytes, bytes
        if name == b"x-client-version":
            client_version = value.decode("utf8")
            break
    else:
        client_version = None

    if not client_version:
        return JSONResponse(
            status_code=401,
            content={"message": "missing client version"},
        )

    if semantic_version.Version(client_version) < semantic_version.Version("2.18.7"):
        message = "version too old, please update your plugin"
        logging.info(message)
        return JSONResponse(
            status_code=401,
            content={"message": message},
        )

    response = await call_next(request)

    return response


app = (
    get_app(settings)
    .use(Supabase(settings.supabase_url, settings.supabase_key))
    .use(version_check)
    .use(History)
    .use(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)

app = app.run()
