import logging
import os
from typing import Annotated

import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.services.wf_engines.argo_engine import ArgoEngine
from app.settings import Settings
from app.utils.openid import OpenIDValidator

security = HTTPBearer()
token_validator = OpenIDValidator()

conf_base_path = os.getenv("SETTINGS_BASE_PATH", "../")
conf_file_path = os.path.join(conf_base_path, "config.yaml")

settings = Settings(config_file=conf_file_path)

# Use the settings in your application
app = FastAPI(root_path=settings.wf_service_settings.root_path)

if settings.wf_service_settings.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def valid_access_token(credentials: Annotated[
    HTTPAuthorizationCredentials, Depends(security)],
                       ):
    try:
        return token_validator.validate(credentials.credentials)
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.PyJWKClientError):
        raise HTTPException(status_code=401, detail="Not authenticated")


def _get_wf_engine(naavrewf2_payload):
    vl_conf = settings.get_vl_config(naavrewf2_payload.virtual_lab)
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
