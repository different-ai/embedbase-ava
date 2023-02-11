import logging
import os
import re
from typing import Tuple, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from firebase_admin import initialize_app, credentials, firestore, auth
import sentry_sdk
from google.cloud.firestore import SERVER_TIMESTAMP
from google.api_core.exceptions import InvalidArgument
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

sentry_sdk.init(
    dsn="https://0ccb093b6ca642d9a173411aacb045b9@o404046.ingest.sentry.io/4504407326851072",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production,
    traces_sample_rate=0.2,
    environment=ENVIRONMENT,
    _experiments={
        "profiles_sample_rate": 1.0,
    },
)
SECRET_FIREBASE_PATH = (
    "/secrets_firebase" if os.path.exists("/secrets_firebase") else ".."
)


if not os.path.exists(SECRET_FIREBASE_PATH + "/svc.prod.json"):
    SECRET_FIREBASE_PATH = "."
cred = credentials.Certificate(SECRET_FIREBASE_PATH + "/svc.prod.json")
initialize_app(cred)
fc = firestore.client()

_IGNORED_PATHS = [
    "openapi.json",
    "redoc",
    "docs",
]
path_transform_regex = re.compile(r"/v1/[^/]+/")

class DetailedError(Exception):
    def __init__(self, scope: dict, status_code: int, detail: str) -> None:
        self.scope = scope
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:
        return self.detail


async def firebase_auth(scope):
        # extract token from header
    for name, value in scope["headers"]:  # type: bytes, bytes
        if name == b"authorization":
            authorization = value.decode("utf8")
            break
    else:
        authorization = None

    if not authorization:
        raise DetailedError(scope, 401, "missing authorization header")

    s = authorization.split(" ")

    if len(s) != 2:
        raise DetailedError(scope, 401, "invalid authorization header")

    token_type, token = s
    assert (
        token_type == "Bearer"
    ), "Authorization header must be `Bearer` type. Like: `Bearer LONG_JWT`"

    try:
        # decoded_token = auth.verify_id_token(token)
        # HACK to skip token expiration etc.
        # TODO: shouldn't check uid also?
        # remove whitespace before and after
        token = token.strip()
        docs = fc.collection("links").where("token", "==", token).get()
        if len(docs) == 0:
            raise DetailedError(scope, 401, "invalid token")
        data = docs[0].to_dict()
    # except auth.ExpiredIdTokenError as err:
        # raise DetailedError(scope, 401, str(err))
    except InvalidArgument as err:
        raise DetailedError(scope, 500, "please delete cache and login again")
    except Exception as err:
        raise DetailedError(scope, 401, str(err))

    # add uid to scope
    scope["uid"] = data["userId"]
    scope["group"] = data.get("group", "default")
    try:
        user: auth.UserRecord = auth.get_user(scope["uid"])
    except:
        raise DetailedError(scope, 401, "invalid uid")
    claims = user.custom_claims or {}
    stripe_role = claims.get("stripeRole", "free")
    scope["stripe_role"] = stripe_role
    return scope["uid"], scope["group"]


plans = {
    "free": {
        "/v1/text/create": 25,
        "/v1/image/create": 5,
        "/v1/search": 15,
    },
    "hobby": {
        "/v1/text/create": 1000,
        "/v1/image/create": 200,
        "/v1/search": 600,
    },
    "pro": {
        "/v1/text/create": 1000,
        "/v1/image/create": 200,
        "/v1/search": 600,
    },
}



async def can_log(user: str, group: str, scope: dict) -> Optional[str]:
    # get all the requests since the beginning of the month (first day)
    current_month_history_by_path_doc = fc.collection("quotas").document(
        user
    ).get()
    # no log yet
    if not current_month_history_by_path_doc.exists:
        return None
    # i.e. {"/v1/text/create": 3, "/v1/image/create": 2 ...}
    current_month_history_by_path = current_month_history_by_path_doc.to_dict()
    stripe_role = scope.get("stripe_role", "free")

    history_path = scope["history_path"]

    if stripe_role == "free":
        p = "/v1/text/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} texts. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )
        p = "/v1/image/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} images. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )
        p = "/v1/search"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} links. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )
    elif stripe_role == "hobby":
        p = "/v1/text/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} texts. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )
        p = "/v1/image/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} images. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )
        p = "/v1/search"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} links. "
                    + "Please upgrade your plan on https://app.anotherai.co"
                )

    elif stripe_role == "pro":
        p = "/v1/text/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} texts. "
                    + "Please contact us at ben@prologe.io to increase your plan limit"
                )
        p = "/v1/image/create"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} images. "
                    + "Please contact us at ben@prologe.io to increase your plan limit"
                )
        p = "/v1/search"
        if history_path == p:
            if current_month_history_by_path.get(p, 0) > plans[stripe_role][p]:
                return (
                    f"You exceeded your plan limit of {plans[stripe_role][p]} links. "
                    + "Please contact us at ben@prologe.io to increase your plan limit"
                )

async def log(user: str, group: str, scope: dict):
    """log the request in the history"""
    metadata = dict(scope)
    del metadata["app"]
    # turn headers [(b"key", b"value"), ...] into {"key": "value", ...}
    metadata["headers"] = dict(
        (k.decode("utf8"), v.decode("utf8")) for k, v in metadata["headers"]
    )
    metadata["path"] = metadata["history_path"]
    fc.collection("history").add(
        {
            "user": user,
            "group": group,
            # TODO: agree & remove all unnecessary fields that are stored in the history
            "scope": metadata,
            "timestamp": SERVER_TIMESTAMP,
        }
    )


async def on_auth_error(exc: Exception, scope: dict):
    status_code = (
        exc.status_code
        if hasattr(exc, "status_code")
        else 500
    )
    message = exc.detail if hasattr(exc, "detail") else str(exc)

    logging.warning(message, exc_info=True)
    if status_code == 500:
        sentry_sdk.capture_message(message, level="error")
    return JSONResponse(
        status_code=status_code,
        content={"message": message},
    )

def middleware(app: FastAPI):
    @app.middleware("http")
    async def history(request: Request, call_next) -> Tuple[str, str]:
        if request.scope["type"] != "http":  # pragma: no cover
            return await call_next(request)

        if "health" in request.scope["path"]:
            return await call_next(request)

        # in development mode, allow redoc, openapi etc
        if ENVIRONMENT == "development" and any(
            path in request.scope["path"] for path in _IGNORED_PATHS
        ):
            return await call_next(request)

        # calculate the user ID and group
        user, group = "local", "development"

        async def _on_error(exc):
            response = await on_auth_error(exc, request.scope)
            return response

        try:
            user, group = await firebase_auth(request.scope)
        except Exception as exc:
            return await _on_error(exc)

        current_path = request.scope["path"]
        # turns "/v1/gbdp609rg6/search" into "/v1/search"
        current_path = path_transform_regex.sub("/v1/", current_path)
        request.scope["history_path"] = current_path
        # check if the user can log this request within his plan
        error = await can_log(user, group, request.scope)
        if error is not None:
            # TODO 402 OK ? https://stackoverflow.com/questions/39221380/what-is-the-http-status-code-for-license-limit-reached
            return await _on_error(Exception(request.scope, 402, error))

        # TODO https://www.notion.so/anotherai/analytics-collecting-prompt-body-226b3bc28a824db9bca799a63dbab054
        # TODO when merged https://github.com/encode/starlette/pull/1692
        # request = Request(scope, receive)
        # json_body = await request.json()
        # scope["body"] = json_body
        await log(user, group, request.scope)
        # return await self.app(scope, receive, send)

        response = await call_next(request)
        return response
