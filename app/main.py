import logging
import os
import shutil
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


def download_file(source, destination):
    # Check if source is a URL
    parsed_url = urlparse(source)

    if parsed_url.scheme in ("http", "https"):  # Remote URL
        try:
            response = requests.get(source, stream=True)
            response.raise_for_status()
            with open(destination, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"File downloaded from {source} to {destination}")
        except requests.RequestException as e:
            print(f"Error downloading remote file: {e}")

    elif os.path.exists(source):  # Local file (relative or absolute path)
        try:
            shutil.copy(source, destination)
            print(f"File copied from local path: {source} to {destination}")
        except Exception as e:
            print(f"Error copying local file: {e}")

    else:
        print(f"Invalid path or URL: {source}")


download_file(os.getenv('CONFIG_FILE_URL', 'https://raw.githubusercontent.com/'
                                           'naavrehub/'
                                           'naavre-workflow-service/'
                                           'main/conf.json'),
              'conf.json')

settings = Settings(config_file='conf.json')

# Use the settings in your application
app = FastAPI(root_path=os.getenv('ROOT_PATH',
                                  '/NaaVRE-workflow-service'))

if os.getenv('DEBUG', 'false').lower() == 'true':
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
