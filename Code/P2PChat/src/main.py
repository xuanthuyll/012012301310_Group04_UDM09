"""Main entry point for the P2P chat application."""

import sys
from gui.app import ChatApp
from gui.validation import validate_port
from config import configure_logging, DEFAULT_LISTEN_PORT

configure_logging()


def main() -> None:
    """Parse command-line arguments and start the chat application."""
    port = DEFAULT_LISTEN_PORT

    if len(sys.argv) > 1:
        port_text = sys.argv[1]

        if not validate_port(port_text):
            print("Invalid port. Use a number from 1 to 65535.")
            return

        port = int(port_text)

    app = ChatApp(listen_port=port)
    app.mainloop()


if __name__ == "__main__":
    main()
