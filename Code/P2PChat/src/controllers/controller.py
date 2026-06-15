"""ChatController: thin adapter between P2PNode and the GUI layer."""
import logging
from typing import Callable, Optional, Tuple

from network.node import P2PNode

logger = logging.getLogger(__name__)


class ChatController:
    """Thin wrapper around P2PNode that exposes a simple controller interface
    for the GUI and ensures callback exceptions are contained.
    """

    def __init__(
        self,
        on_system: Callable[[str], None],
        on_message: Callable[[str, str], None],
        on_connected: Callable[[str], None],
        on_disconnect: Callable[[str], None],
        on_peers_update: Callable[[], None],
        on_peer_discovered: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self.on_system = on_system
        self.on_message = on_message
        self.on_connected = on_connected
        self.on_disconnect = on_disconnect
        self.on_peers_update = on_peers_update
        self.on_peer_discovered = on_peer_discovered

        self.node: Optional[P2PNode] = None

    # ------------------------------------------------------------------ #
    # Node lifecycle                                                       #
    # ------------------------------------------------------------------ #

    def start_node(self, host: str, port: int, username: str) -> Tuple[bool, str]:
        """Start the P2PNode server and discovery service. Returns (success, message)."""
        if self.node is not None:
            return False, "Node already started."

        self.node = P2PNode(
            host=host,
            port=port,
            username=username,
            on_message = self._on_message,
            on_disconnect = self._on_disconnect,
            on_connected = self._on_connected,
            on_peer_discovered = self._on_peer_discovered,
        )

        try:
            self.node.start_server()
        except OSError:
            logger.exception("Failed to start node")
            self.node = None
            return False, f"Could not bind to port {port}."

        return True, f"Started as '{username}' — listening on port {port}."

    def stop(self) -> None:
        """Stop the P2PNode server and discovery service."""
        if self.node is not None:
            self.node.stop_server()
            self.node = None

    # ------------------------------------------------------------------ #
    # Networking actions                                                   #
    # ------------------------------------------------------------------ #

    def connect_to_peer(self, ip: str, port: int) -> bool:
        """Connect to a peer at the given IP and port. Returns success."""
        if self.node is None:
            self.on_system("Start the node first.")
            return False
        return self.node.connect_to_peer(ip, port)

    def send_message(self, payload: str, peer_address: str) -> bool:
        """Send a message to a specific peer. Returns success."""
        if self.node is None:
            self.on_system("Start the node first.")
            return False
        return self.node.send_message(payload, peer_address)

    def broadcast_message(self, payload: str) -> Tuple[int, int]:
        """Broadcast a message to all connected peers. Returns (success_count, total_peers)."""
        if self.node is None:
            self.on_system("Start the node first.")
            return 0, 0
        return self.node.broadcast_message(payload)

    def discover_peers(self) -> None:
        """Trigger peer discovery. Results will come in via the on_peer_discovered callback."""
        if self.node is not None:
            self.node.discover_peers()

    def get_discovered_peers(self) -> dict[str, dict]:
        """Get the current list of discovered peers. Returns a dict of peer_address -> info."""
        if self.node is not None:
            return self.node.get_discovered_peers()
        return {}

    # ------------------------------------------------------------------ #
    # Internal safe callback forwarders                                   #
    # ------------------------------------------------------------------ #

    def _safe_fire(self, cb: Callable, *args) -> None:
        try:
            cb(*args)
        except Exception:
            logger.exception("Controller callback raised an exception")

    def _on_message(self, sender: str, payload: str) -> None:
        self._safe_fire(self.on_message, sender, payload)

    def _on_connected(self, peer_address: str) -> None:
        self._safe_fire(self.on_connected, peer_address)
        self._safe_fire(self.on_peers_update)

    def _on_disconnect(self, peer_address: str) -> None:
        self._safe_fire(self.on_disconnect, peer_address)
        self._safe_fire(self.on_peers_update)

    def _on_peer_discovered(self, peer_address: str, info: dict) -> None:
        if self.on_peer_discovered is not None:
            self._safe_fire(self.on_peer_discovered, peer_address, info)
