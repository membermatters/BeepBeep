import usocket
import ulogging
import config

ulogging.basicConfig(level=config.LOG_LEVEL)
logger = ulogging.getLogger("httpserver")

sock = None


def setup_http_server():
    global sock

    try:
        # setup our HTTP server
        sock = usocket.socket()

        # s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
        sock.bind(usocket.getaddrinfo("0.0.0.0", 80)[0][-1])
        sock.listen(2)
        return True
    except Exception as e:
        logger.error("Got exception when setting up HTTP server")
        logger.error(str(e))
        return False


def client_response(conn):
    response = """
            {"success": true}
            """

    conn.send("HTTP/1.1 200 OK\n")
    conn.send("Content-Type: application/json\n")
    conn.send("Connection: close\n\n")
    conn.sendall(response)
    conn.close()
