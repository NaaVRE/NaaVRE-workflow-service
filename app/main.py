import logging
import os
from typing import Annotated

import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.services.wf_engines.argo_engine import ArgoEngine
from app.utils.openid import OpenIDValidator

security = HTTPBearer()
token_validator = OpenIDValidator()


class Settings(BaseSettings):
    root_path: str = "my-root-path"
    if not root_path.startswith("/"):
        root_path = "/" + root_path
    if root_path.endswith("/"):
        root_path = root_path[:-1]


settings = Settings()

app = FastAPI(root_path=settings.root_path)

if os.getenv("DEBUG", "false").lower() == "true":
    logging.basicConfig(level=10)


def valid_access_token(credentials: Annotated[
    HTTPAuthorizationCredentials, Depends(security)],
                       ):
    try:
        return token_validator.validate(credentials.credentials)
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.PyJWKClientError):
        raise HTTPException(status_code=401, detail="Not authenticated")


def get_vl_config(virtual_lab: str):
    return {}


def _get_wf_engine(naavrewf2_payload):
    vl_conf = get_vl_config(naavrewf2_payload.virtual_lab)
    wf_engine_name = vl_conf['wf_engine']
    if wf_engine_name == "argo":
        return ArgoEngine(naavrewf2_payload, vl_conf)
    pass


@app.post("/submit")
def submit(access_token: Annotated[dict, Depends(valid_access_token)],
           naavrewf2_payload: Naavrewf2Payload):
    naavrewf2_payload.set_user_name(access_token['preferred_username'])
    wf_engine = _get_wf_engine(naavrewf2_payload)
    print(wf_engine)
    return {"run_url": "https://example.org/", "naavrewf2": None}


@app.post("/convert")
def convert(access_token: Annotated[dict, Depends(valid_access_token)],
            naavrewf2_payload: Naavrewf2Payload):
    return {"workflow": "invalid"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
