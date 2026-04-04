import string
import random
import requests

def gen_code(n=6):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))

def api(method, path, base, **kwargs):
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=5, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"raw": r.text}
    except requests.exceptions.ConnectionError:
        return None, {"error": f"Cannot connect to {base}"}
    except Exception as e:
        return None, {"error": str(e)}

def probe(base, path):
    try:
        r = requests.get(f"{base.rstrip('/')}/{path.lstrip('/')}", timeout=3)
        return r.status_code == 200, r.json() if r.ok else {}
    except Exception:
        return False, {}
