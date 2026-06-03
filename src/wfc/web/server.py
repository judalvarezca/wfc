from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Launch the FastAPI app via uvicorn."""
    import uvicorn

    logger.info("starting wfc web server on http://%s:%d", host, port)
    uvicorn.run("wfc.web.app:app", host=host, port=port, reload=reload)
