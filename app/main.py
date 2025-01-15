import logging
import os
from typing import Annotated

import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings



from app.models.naavrewf2_payload import Naavrewf2Payload
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





@app.post("/submit")
def extract_cell(access_token: Annotated[dict, Depends(valid_access_token)],
                 naavrewf2_payload: Naavrewf2Payload):
    return {"run_url":"https://example.org/","naavrewf2":None}


@app.post("/convert")
def containerize(access_token: Annotated[dict, Depends(valid_access_token)],
                 naavrewf2_payload: Naavrewf2Payload):
    return {"workflow": "invalid"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
