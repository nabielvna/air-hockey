import socket
from concurrent.futures import ThreadPoolExecutor
from server.http_handler import HttpServer 

HTTP_PORT = 8000
httpserver = HttpServer()

def process_the_client(connection, address):
    try:
        header_data = b""
        connection.settimeout(1) 
        while True:
            try:
                chunk = connection.recv(1024)
                if not chunk:
                    break
                header_data += chunk
                if b"\r\n\r\n" in header_data:
                    break
            except socket.timeout:
                break
        
        print("---- REQUEST RECEIVED ----")
        print(header_data.decode('utf-8', errors='ignore'))
        print("--------------------------")
        
        if not header_data:
            connection.close()
            return

        parts = header_data.split(b"\r\n\r\n", 1)
        header_part = parts[0]
        body_part = parts[1] if len(parts) > 1 else b""
        
        headers = header_part.decode('utf-8').split('\r\n')
        
        content_length = 0
        for h in headers:
            if h.lower().startswith('content-length:'):
                try:
                    content_length = int(h.split(':')[1].strip())
                    break
                except (ValueError, IndexError):
                    pass
        
        while len(body_part) < content_length:
            try:
                chunk = connection.recv(1024)
                if not chunk:
                    break
                body_part += chunk
            except socket.timeout:
                break
            
        full_request_str = header_part.decode('utf-8') + '\r\n\r\n' + body_part.decode('utf-8', errors='ignore')
        
        result = httpserver.process_request(full_request_str)
        connection.sendall(result)

    except Exception as e:
        print(f"Error processing client {address}: {e}")
    finally:
        connection.close()


def run_http_server():
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.bind(('0.0.0.0', HTTP_PORT))
    my_socket.listen(5)
    print(f"HTTP server running on port {HTTP_PORT}...")

    with ThreadPoolExecutor(max_workers=20) as executor:
        while True:
            connection, client_address = my_socket.accept()
            executor.submit(process_the_client, connection, client_address)

if __name__ == "__main__":
    run_http_server()