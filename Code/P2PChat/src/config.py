"""Central configuration and logging setup for the application."""
import logging

DEFAULT_LISTEN_PORT = 12000
DISCOVERY_PORT = 15000

def configure_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
