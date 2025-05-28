import json
import logging
import os
from typing import Annotated
from urllib.parse import urlparse

import cachetools.func
import jwt
import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.naavrewf2_payload import Naavrewf2Payload
from app.services.wf_engines.argo_engine import ArgoEngine
from app.settings.service_settings import Settings
from app.utils.openid import OpenIDValidator

security = HTTPBearer()
token_validator = OpenIDValidator()


@cachetools.func.ttl_cache(ttl=6 * 3600)
def load_configuration(source):
    # Check if source is a URL
    parsed_url = urlparse(source)
    if parsed_url.scheme in ("http", "https"):  # Remote URL
        response = requests.get(source)
        return response.json()
    elif os.path.exists(source):  # Local file (relative or absolute path)
        with open(source, "r", encoding="utf-8") as file:
            data_dict = json.load(file)
        file.close()
        return data_dict

    else:
        raise Exception('Invalid configuration source')


config_file = os.getenv('CONFIG_FILE_URL', 'https://raw.githubusercontent.com/'
                                           'naavrehub/'
                                           'naavre-workflow-service/'
                                           'main/conf.json')

conf = None
if os.path.exists(config_file):
    conf = load_configuration(config_file)
else:
    # Start going up the directory tree until we find the configuration file
    current_dir = os.getcwd()
    while current_dir != '/':
        config_path = os.path.join(current_dir,
                                   os.getenv('CONFIG_FILE_URL',
                                             'configuration.json'))
        if os.path.exists(config_path):
            conf = load_configuration(config_path)
            break
        current_dir = os.path.dirname(current_dir)

settings = Settings(config=conf)

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


def _get_wf_engine(virtual_lab: str = None):
    vl_conf = settings.get_vl_config(virtual_lab)
    if not vl_conf:
        raise HTTPException(status_code=404, detail="Virtual lab not found")
    if vl_conf and vl_conf.wf_engine_config.name == "argo":
        return ArgoEngine(vl_conf)
    else:
        raise HTTPException(status_code=422, detail="Invalid configuration")


@app.post("/submit")
def submit(access_token: Annotated[dict, Depends(valid_access_token)],
           naavrewf2_payload: Naavrewf2Payload):
    naavrewf2_payload.set_user_name(access_token['decoded']
                                    ['preferred_username'])

    wf_engine = _get_wf_engine(virtual_lab=naavrewf2_payload.virtual_lab)
    wf_engine.set_payload(naavrewf2_payload)
    response = wf_engine.submit(user_jwt=access_token['raw'])
    return response


@app.post("/convert")
def convert(access_token: Annotated[dict, Depends(valid_access_token)],
            naavrewf2_payload: Naavrewf2Payload):
    naavrewf2_payload.set_user_name(access_token['decoded']
                                    ['preferred_username'])
    wf_engine = _get_wf_engine(virtual_lab=naavrewf2_payload.virtual_lab)
    wf_engine.set_payload(naavrewf2_payload)
    return wf_engine.naavrewf2_2_argo_workflow()


@app.get('/status/{virtual_lab}')
def get_status(
        access_token: Annotated[dict, Depends(valid_access_token)],
        virtual_lab: str,
        workflow_url: str = Query()):
    wf_engine = _get_wf_engine(virtual_lab=virtual_lab)
    argo_wf = wf_engine.get_wf(workflow_url, user_jwt=access_token['raw'])
    return {'status': argo_wf['status']}


@app.delete('/delete/{virtual_lab}')
def delete_wf(
        access_token: Annotated[dict, Depends(valid_access_token)],
        virtual_lab: str,
        workflow_url: str = Query()):
    wf_engine = _get_wf_engine(virtual_lab=virtual_lab)
    wf_engine.delete(workflow_url)
    return {'status': 'deleted'}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
