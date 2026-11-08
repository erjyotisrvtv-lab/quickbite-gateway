from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("quickbite_gateway_testmod", Path(__file__).parents[1]/"main.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app=module.app

def test_health_and_web_ui():
    with TestClient(app) as c:
        assert c.get('/health').json()['status']=='ok'
        assert 'QuickBite' in c.get('/').text
        assert c.get('/api/unknown/health').status_code==404
