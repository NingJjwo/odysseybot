from flask import Flask
from threading import Thread

class WebServer:
    def __init__(self):
        self.app = Flask('')
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/')
        def home():
            return "Bot is alive!"
    
    def run(self):
        self.app.run(host="0.0.0.0", port=8080)
    
    def keep_alive(self):
        t = Thread(target=self.run)
        t.daemon = True
        t.start()

# Create instance for easy import
webserver = WebServer()

# For backward compatibility
def keep_alive():
    webserver.keep_alive()