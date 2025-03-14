from pathlib import Path
import json
import logging
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
logger = logging.getLogger(__name__)
tests_resources_dir = Path(__file__).parent / "resources"

def test_submit():
    for filename in (tests_resources_dir / "naavrewf2_payload").iterdir():
        with open(filename) as f:
            payload = json.load(f)
        response = client.post(
            '/submit/',
            headers={'Authorization': 'Bearer ' + os.getenv('AUTH_TOKEN')},
            json=payload,
            )
        logger.debug(response.json())
        assert response.status_code == 200
