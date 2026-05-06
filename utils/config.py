import os
import json
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".musichub_config.json")
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}
def save_config(data):
    try:
        cfg = load_config()
        cfg.update(data)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
