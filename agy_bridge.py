# Обратная совместимость: agy_bridge.py -> bridge.py
from bridge import *

if __name__ == "__main__":
    import uvicorn
    import bridge
    port = bridge.config["port"]
    uvicorn.run(bridge.app, host="0.0.0.0", port=port)
