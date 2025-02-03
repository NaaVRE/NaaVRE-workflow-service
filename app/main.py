import json
import logging
import os
from typing import Annotated
from urllib.parse import urlparse

import jwt
import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.services.wf_engines.argo_engine import ArgoEngine
from app.settings import Settings
from app.utils.openid import OpenIDValidator

security = HTTPBearer()
token_validator = OpenIDValidator()


def load_configuration(source):
    # Check if source is a URL
    parsed_url = urlparse(source)

    if parsed_url.scheme in ("http", "https"):  # Remote URL
        try:
            response = requests.get(source)
            return response.json()
        except requests.RequestException as e:
            print(f"Error opening remote file: {e}")

    elif os.path.exists(source):  # Local file (relative or absolute path)
        try:
            with open(source, "r", encoding="utf-8") as file:
                data_dict = json.load(file)
            file.close()
            return data_dict
        except Exception as e:
            print(f"Error copying local file: {e}")

    else:
        raise Exception('Invalid configuration source')


conf = load_configuration(
    os.getenv('CONFIG_FILE_URL', 'https://raw.githubusercontent.com/'
                                 'naavrehub/'
                                 'naavre-workflow-service/'
                                 'main/conf.json'))

settings = Settings(config=conf)
# Use the settings in your application
app = FastAPI(root_path=os.getenv('ROOT_PATH',
                                  '/NaaVRE-workflow-service'))

if os.getenv('DEBUG', 'false').lower() == 'true':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def valid_access_token(credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(security)]):
    try:
        return token_validator.validate(credentials.credentials)
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.PyJWKClientError):
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


def _get_wf_engine(naavrewf2_payload):
    vl_conf = settings.get_vl_config(naavrewf2_payload.virtual_lab)

    if vl_conf.wf_engine.name == "argo":
        return ArgoEngine(naavrewf2_payload, vl_conf)
    else:
        raise HTTPException(status_code=422, detail="Invalid configuration")


@app.post("/submit")
def submit(access_token: Annotated[dict, Depends(valid_access_token)],
           naavrewf2_payload: Naavrewf2Payload):
    naavrewf2_payload.set_user_name(access_token['preferred_username'])

    wf_engine = _get_wf_engine(naavrewf2_payload)
    wf_engine.submit()
    return {"run_url": "https://example.org/", "naavrewf2": None}


@app.post("/convert")
def convert(access_token: Annotated[dict, Depends(valid_access_token)],
            naavrewf2_payload: Naavrewf2Payload):
    return {"workflow": "invalid"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
