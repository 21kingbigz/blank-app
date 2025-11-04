# api/index.py
import subprocess
import threading
import time
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

# This is the port Streamlit will run on internally
STREAMLIT_PORT = os.environ.get("STREAMLIT_PORT", "8501")

# This function will start Streamlit in a new thread
def start_streamlit():
    print("Starting Streamlit...")
    cmd = [
        "streamlit", "run", "streamlit_app.py",
        "--server.port", STREAMLIT_PORT,
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false"
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Streamlit process exited with error: {e}")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

# Start Streamlit in a separate thread
# This prevents the main Vercel server from blocking
threading.Thread(target=start_streamlit, daemon=True).start()

# Give Streamlit a moment to start up
time.sleep(5) # You might need to adjust this depending on app size

# Simple HTTP server to proxy requests to Streamlit
class StreamlitProxy(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(307) # Temporary Redirect
        self.send_header('Location', f'http://localhost:{STREAMLIT_PORT}{self.path}')
        self.end_headers()

    def do_POST(self):
        self.send_response(307) # Temporary Redirect
        self.send_header('Location', f'http://localhost:{STREAMLIT_PORT}{self.path}')
        self.end_headers()

# Create the proxy server
if __name__ == '__main__':
    # Vercel provides the port to listen on via process.env.PORT
    # Use this to run our proxy server
    vercel_port = int(os.environ.get("PORT", 8080))
    httpd = HTTPServer(("", vercel_port), StreamlitProxy)
    print(f"Vercel proxy server running on port {vercel_port} and redirecting to Streamlit on {STREAMLIT_PORT}")
    httpd.serve_forever()

# Vercel uses WSGI/ASGI for Python. We'll use a simple proxy for our Streamlit app.
# For more complex Streamlit apps or larger scale, you might use Gunicorn or Waitress directly.
# This basic setup usually works for simple Vercel deployments.
