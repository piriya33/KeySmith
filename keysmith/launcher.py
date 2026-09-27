from __future__ import annotations

import multiprocessing
import os
import secrets
from threading import Timer
import webbrowser

from werkzeug.serving import make_server

from keysmith.app import create_app


def main() -> None:
    multiprocessing.freeze_support()
    host = "127.0.0.1"
    port = int(os.environ.get("KEYSMITH_PORT", "0"))
    server_holder = {}

    def shutdown() -> None:
        server_holder["server"].shutdown()

    app = create_app(
        shutdown_callback=shutdown,
        shutdown_token=secrets.token_urlsafe(32),
    )
    server = make_server(host, port, app, threaded=True)
    server_holder["server"] = server
    url = f"http://{host}:{server.server_port}"

    def open_browser() -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    print(f"Keysmith running at {url}")
    if os.environ.get("KEYSMITH_NO_BROWSER") != "1":
        Timer(0.35, open_browser).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
