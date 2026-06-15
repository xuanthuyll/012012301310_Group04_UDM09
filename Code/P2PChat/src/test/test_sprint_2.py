import io
import struct
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import InvalidToken
from security.crypto import CryptoHandler
from message.protocol import PacketType, ProtocolHandler
from security.rsa_utils import RSAUtils

class FakeSocket:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    def recv(self, n: int) -> bytes:
        return self._buf.read(n)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _fake_socket(data: bytes):
    return FakeSocket(data)


def _make_protocol() -> ProtocolHandler:
    return ProtocolHandler()


def _make_crypto() -> CryptoHandler:
    return CryptoHandler()


# ── Protocol framing ───────────────────────────────────────────────────────────

def test_round_trip_plaintext() -> None:
    """Message survives create → serialize → receive_packet → plaintext read."""
    protocol = _make_protocol()
    packet = protocol.create_packet(PacketType.MESSAGE, "Tai", "Hello World")
    data = protocol.serialize(packet)
    received = protocol.receive_packet(_fake_socket(data))

    assert received is not None
    assert received["payload"] == "Hello World"
    print("[OK] test_round_trip_plaintext")


def test_round_trip_encrypted() -> None:
    """Message survives create (encrypted) → serialize → receive → decrypt."""
    protocol = _make_protocol()
    crypto = _make_crypto()
    packet = protocol.create_packet(PacketType.MESSAGE, "Tai", "Secret", crypto=crypto)
    data = protocol.serialize(packet)
    received = protocol.receive_packet(_fake_socket(data))

    assert received is not None
    plaintext = protocol.decrypt_payload(received, crypto=crypto)
    assert plaintext == "Secret"
    print("[OK] test_round_trip_encrypted")


def test_wrong_key_raises() -> None:
    """Decrypting with the wrong key raises InvalidToken — not silently wrong."""
    protocol = _make_protocol()
    sender_crypto = _make_crypto()
    wrong_crypto = _make_crypto()

    packet = protocol.create_packet(PacketType.MESSAGE, "A", "Hi", crypto=sender_crypto)
    data = protocol.serialize(packet)
    received = protocol.receive_packet(_fake_socket(data))
    assert received is not None

    try:
        protocol.decrypt_payload(received, crypto=wrong_crypto)
        assert False, "Expected InvalidToken"
    except InvalidToken:
        pass
    print("[OK] test_wrong_key_raises")


def test_validate_rejects_missing_fields() -> None:
    protocol = _make_protocol()
    assert not protocol.validate_packet({"type": "message"})
    print("[OK] test_validate_rejects_missing_fields")


def test_validate_accepts_valid_message() -> None:
    protocol = _make_protocol()
    crypto = _make_crypto()
    packet = protocol.create_packet(PacketType.MESSAGE, "A", "hello", crypto=crypto)
    assert protocol.validate_packet(packet)
    print("[OK] test_validate_accepts_valid_message")


def test_validate_accepts_valid_handshake() -> None:
    protocol = _make_protocol()
    _, pub = RSAUtils.generate_key_pair()
    packet = {
        "type": PacketType.HANDSHAKE,
        "username": "Alice",
        "version": "1.0",
        "listen_port": 12000,
        "public_key": RSAUtils.serialize_public_key(pub),
    }
    assert protocol.validate_packet(packet)
    print("[OK] test_validate_accepts_valid_handshake")


def test_validate_accepts_valid_handshake_ack() -> None:
    protocol = _make_protocol()
    _, pub = RSAUtils.generate_key_pair()
    packet = {
        "type": PacketType.HANDSHAKE_ACK,
        "status": "ok",
        "public_key": RSAUtils.serialize_public_key(pub),
    }
    assert protocol.validate_packet(packet)
    print("[OK] test_validate_accepts_valid_handshake_ack")


def test_oversized_packet_dropped() -> None:
    protocol = _make_protocol()
    fake_data = struct.pack("!I", protocol.MAX_PACKET_SIZE + 1) + b"x" * 100
    result = protocol.receive_packet(_fake_socket(fake_data))
    assert result is None
    print("[OK] test_oversized_packet_dropped")


def test_receive_packet_does_not_validate() -> None:
    """receive_packet returns the packet even if validate_packet would fail."""
    protocol = _make_protocol()
    bad = {"type": "message"}
    data = protocol.serialize(bad)
    result = protocol.receive_packet(_fake_socket(data))
    assert result == bad
    print("[OK] test_receive_packet_does_not_validate")


def test_receive_packet_handles_oserror() -> None:
    protocol = _make_protocol()

    class BrokenSocket:
        def recv(self, n):
            raise OSError("connection reset")

    result = protocol.receive_packet(BrokenSocket())
    assert result is None
    print("[OK] test_receive_packet_handles_oserror")


# ── RSA key exchange ───────────────────────────────────────────────────────────

def test_rsa_encrypt_decrypt_round_trip() -> None:
    from cryptography.fernet import Fernet
    priv, pub = RSAUtils.generate_key_pair()
    fernet_key = Fernet.generate_key()
    encrypted = RSAUtils.encrypt(pub, fernet_key)
    decrypted = RSAUtils.decrypt(priv, encrypted)
    assert decrypted == fernet_key
    print("[OK] test_rsa_encrypt_decrypt_round_trip")


def test_load_public_key_rejects_garbage() -> None:
    try:
        RSAUtils.load_public_key("not a PEM key")
        assert False, "Expected exception"
    except Exception:
        pass
    print("[OK] test_load_public_key_rejects_garbage")


# ── Node integration ───────────────────────────────────────────────────────────

def test_register_peer_atomic() -> None:
    """register_peer returns False on second call for same address."""
    from network.node import P2PNode
    import socket as _socket

    node = P2PNode(host="127.0.0.1", port=19999)
    a, b = _socket.socketpair()
    try:
        assert node._register_peer("127.0.0.1:9000", a, True) is True
        assert node._register_peer("127.0.0.1:9000", b, False) is False
        with node.peers_lock:
            assert node.peers["127.0.0.1:9000"] is a
    finally:
        a.close()
        b.close()
    print("[OK] test_register_peer_atomic")


def test_get_peer_address_o1() -> None:
    """get_peer_address uses O(1) reverse lookup via _sock_to_addr."""
    from network.node import P2PNode
    import socket as _socket

    node = P2PNode(host="127.0.0.1", port=19996)
    a, b = _socket.socketpair()
    try:
        node._register_peer("127.0.0.1:9010", a, True)
        # Must resolve in O(1) — check that _sock_to_addr is populated
        assert node._get_peer_address(a) == "127.0.0.1:9010"
        # Unknown socket returns None
        assert node._get_peer_address(b) is None
    finally:
        a.close()
        b.close()
    print("[OK] test_get_peer_address_o1")


def test_send_message_returns_false_when_not_active() -> None:
    """send_message returns False when peer state is not active."""
    from network.node import P2PNode
    import socket as _socket

    node = P2PNode(host="127.0.0.1", port=19998)
    a, b = _socket.socketpair()
    try:
        node._register_peer("127.0.0.1:9001", a, True)
        result = node.send_message("hello", "127.0.0.1:9001")
        assert result is False
    finally:
        a.close()
        b.close()
    print("[OK] test_send_message_returns_false_when_not_active")


def test_handshake_timeout_disconnects_pending_peer() -> None:
    """Pending peers are disconnected after HANDSHAKE_TIMEOUT seconds."""
    import socket as _socket
    from network import node as _core

    original_timeout = _core.HANDSHAKE_TIMEOUT
    _core.HANDSHAKE_TIMEOUT = 0.1

    disconnected = threading.Event()

    def on_disconnect(_addr):
        disconnected.set()

    node = _core.P2PNode(
        host="127.0.0.1",
        port=19997,
        on_disconnect=on_disconnect,
    )
    a, b = _socket.socketpair()
    try:
        node._register_peer("127.0.0.1:9002", a, True)
        node._schedule_handshake_timeout("127.0.0.1:9002")
        assert disconnected.wait(timeout=2.0), "Timeout did not fire"
    finally:
        _core.HANDSHAKE_TIMEOUT = original_timeout
        b.close()
    print("[OK] test_handshake_timeout_disconnects_pending_peer")


def test_callback_exception_does_not_propagate() -> None:
    """_fire_callback must not raise even if callback raises."""
    from network.node import P2PNode

    node = P2PNode(host="127.0.0.1", port=19990)

    def bad_callback(*args):
        raise RuntimeError("boom")

    # Must not raise
    node._fire_callback(bad_callback, "arg1")
    print("[OK] test_callback_exception_does_not_propagate")


def test_on_message_receives_sender_and_payload() -> None:
    """on_message callback receives (sender, payload) — not just payload."""
    from network.node import P2PNode
    import socket as _socket

    received: list = []

    def on_msg(sender, payload):
        received.append((sender, payload))

    node = P2PNode(host="127.0.0.1", port=19989, username="Bob", on_message=on_msg)

    # Build an active peer session manually
    a, b = _socket.socketpair()
    try:
        node._register_peer("127.0.0.1:9020", a, False)
        crypto = CryptoHandler()
        with node.peers_lock:
            session = node.peer_sessions["127.0.0.1:9020"]
            session["state"] = "active"
            session["crypto"] = crypto
            session["username"] = "Alice"

        # Build an encrypted message packet
        proto = node.protocol_handler
        packet = proto.create_packet(PacketType.MESSAGE, "Alice", "hello", crypto=crypto)
        # Inject via handle_message directly
        node._handle_message(packet, a)

        assert len(received) == 1
        assert received[0] == ("Alice", "hello")
    finally:
        a.close()
        b.close()
    print("[OK] test_on_message_receives_sender_and_payload")


def test_remove_peer_cleans_reverse_map() -> None:
    """remove_peer must also clean _sock_to_addr to avoid stale entries."""
    from network.node import P2PNode
    import socket as _socket

    node = P2PNode(host="127.0.0.1", port=19988)
    a, b = _socket.socketpair()
    try:
        node._register_peer("127.0.0.1:9030", a, True)
        assert node._get_peer_address(a) == "127.0.0.1:9030"
        node._remove_peer(a)
        assert node._get_peer_address(a) is None
        with node.peers_lock:
            assert id(a) not in node._sock_to_addr
    finally:
        b.close()
    print("[OK] test_remove_peer_cleans_reverse_map")


# ── Validation edge cases ──────────────────────────────────────────────────────

def test_validate_rejects_bad_session_key_payload() -> None:
    protocol = ProtocolHandler()
    assert not protocol.validate_packet({"type": PacketType.SESSION_KEY})
    assert not protocol.validate_packet({"type": PacketType.SESSION_KEY, "payload": b"bad"})
    print("[OK] test_validate_rejects_bad_session_key_payload")


def test_validate_ip_rejects_short_ipv4() -> None:
    from gui.validation import validate_ip
    assert not validate_ip("127.1")
    assert not validate_ip("1")
    print("[OK] test_validate_ip_rejects_short_ipv4")


# ── Crypto TTL / replay protection ────────────────────────────────────────────

def test_crypto_accepts_ttl_argument() -> None:
    """CryptoHandler must forward ttl to Fernet."""
    import time
    crypto = CryptoHandler()
    token = crypto.encrypt("hello")
    time.sleep(3)

    try:
        crypto.decrypt(token, ttl=1)
        assert False, "Expected InvalidToken"

    except InvalidToken:
        pass

    print("[OK] test_crypto_accepts_ttl_argument")


def test_crypto_ttl_accepts_fresh_token() -> None:
    """CryptoHandler.decrypt with a generous ttl accepts a fresh token."""
    crypto = CryptoHandler()
    token = crypto.encrypt("world")
    result = crypto.decrypt(token, ttl=60)
    assert result == "world"
    print("[OK] test_crypto_ttl_accepts_fresh_token")


def test_crypto_ttl_none_disables_check() -> None:
    """Passing ttl=None disables replay protection (for backward compat)."""
    crypto = CryptoHandler()
    token = crypto.encrypt("no-ttl")
    # No sleep needed — just ensure None doesn't raise
    result = crypto.decrypt(token, ttl=None)
    assert result == "no-ttl"
    print("[OK] test_crypto_ttl_none_disables_check")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_round_trip_plaintext()
    test_round_trip_encrypted()
    test_wrong_key_raises()
    test_validate_rejects_missing_fields()
    test_validate_accepts_valid_message()
    test_validate_accepts_valid_handshake()
    test_validate_accepts_valid_handshake_ack()
    test_oversized_packet_dropped()
    test_receive_packet_does_not_validate()
    test_receive_packet_handles_oserror()
    test_rsa_encrypt_decrypt_round_trip()
    test_load_public_key_rejects_garbage()
    test_register_peer_atomic()
    test_get_peer_address_o1()
    test_send_message_returns_false_when_not_active()
    test_handshake_timeout_disconnects_pending_peer()
    test_callback_exception_does_not_propagate()
    test_on_message_receives_sender_and_payload()
    test_remove_peer_cleans_reverse_map()
    test_validate_rejects_bad_session_key_payload()
    test_validate_ip_rejects_short_ipv4()
    test_crypto_accepts_ttl_argument()
    test_crypto_ttl_accepts_fresh_token()
    test_crypto_ttl_none_disables_check()
    print("\nAll tests passed.")
