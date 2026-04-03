from http import HTTPStatus
import json
import logging
import os
import sys
from typing import Any, cast

import certifi
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import service
import utils
from models import V1RequestBase

logger = logging.getLogger(__name__)

env_proxy_url = os.environ.get("PROXY_URL", None)
env_proxy_username = os.environ.get("PROXY_USERNAME", None)
env_proxy_password = os.environ.get("PROXY_PASSWORD", None)


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _log_request(request: Request, status_code: int) -> None:
    if request.url.path.endswith("/health"):
        return

    remote_addr = request.client.host if request.client is not None else "-"
    try:
        status_text = f"{status_code} {HTTPStatus(status_code).phrase}"
    except ValueError:
        status_text = str(status_code)

    logger.info(
        "%s %s %s %s",
        remote_addr,
        request.method,
        str(request.url),
        status_text,
    )


def _apply_proxy_env(data: dict[str, Any]) -> dict[str, Any]:
    proxy = data.get("proxy")
    if (
        not proxy
        and env_proxy_url is not None
        and (env_proxy_username is None and env_proxy_password is None)
    ):
        logger.info("Using proxy URL ENV")
        data["proxy"] = {"url": env_proxy_url}
    if (
        not proxy
        and env_proxy_url is not None
        and (env_proxy_username is not None or env_proxy_password is not None)
    ):
        logging.info("Using proxy URL, username & password ENVs")
        data["proxy"] = {
            "url": env_proxy_url,
            "username": env_proxy_username,
            "password": env_proxy_password,
        }
    return data


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as exc:
        response = JSONResponse(status_code=500, content={"error": str(exc)})

    _log_request(request, response.status_code)
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": f"Not found: '{request.url.path}'", "status_code": 404},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400, content={"error": str(exc), "status_code": 400}
    )


@app.get("/")
async def index():
    """
    Show welcome message
    """
    res = service.index_endpoint()
    payload = utils.object_to_dict(res)
    return payload


@app.get("/health")
async def health():
    """
    Healthcheck endpoint.
    This endpoint is special because it doesn't print traces
    """
    res = service.health_endpoint()
    payload = utils.object_to_dict(res)
    return payload



@app.post("/v1")
async def controller_v1(request: Request):
    """
    Controller v1
    """
    raw_body = await request.body()
    data = cast(dict[str, Any], json.loads(raw_body or b"{}"))
    data = _apply_proxy_env(data)
    req = V1RequestBase(data)
    res = service.controller_v1_endpoint(req)
    payload = utils.object_to_dict(res)
    if res.__error_500__:
        return JSONResponse(status_code=500, content=payload)
    return payload


if __name__ == "__main__":
    # fix for HEADLESS=false in Windows binary
    # https://stackoverflow.com/a/27694505
    if os.name == "nt":
        import multiprocessing

        multiprocessing.freeze_support()

    # fix ssl certificates for compiled binaries
    # https://github.com/pyinstaller/pyinstaller/issues/7229
    # https://stackoverflow.com/q/55736855
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["SSL_CERT_FILE"] = certifi.where()

    # validate configuration
    log_level = os.environ.get("LOG_LEVEL", "info").upper()
    log_file = os.environ.get("LOG_FILE", None)
    server_host = os.environ.get("HOST", "0.0.0.0")
    server_port = int(os.environ.get("PORT", 8191))
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s/%(name)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)]
        if log_file
        else [logging.StreamHandler(sys.stdout)],
    )

    # disable warning traces from urllib3
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(
        logging.WARNING
    )
    logging.getLogger("undetected").setLevel(logging.WARNING)
    logging.getLogger("seleniumwire.handler").setLevel(logging.WARNING)
    logging.getLogger("mitmproxy.proxy.server").setLevel(logging.WARNING)

    logger.info(f"FlareSolverr {utils.get_flaresolverr_version()}")
    logger.debug("Debug log enabled")

    # Get current OS for global variable
    utils.get_current_platform()

    # test browser installation
    service.test_browser_installation()

    uvicorn.run(
        app,
        host=server_host,
        port=server_port,
        log_config=None,
        access_log=False,
    )
