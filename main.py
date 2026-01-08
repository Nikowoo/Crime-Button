import http.server
import socketserver
import threading
import os
import webbrowser
import keyboard
import time
import subprocess
import psutil

# define gloabls
PORT = 8000
my_server = None
server_thread = None
lock = threading.Lock()
space_down = False
console_proc = None
caddy_proc = None
log_file = "app.log"

LOG_TITLE = "LOGS"

# logging 
def write_log(msg):
    try:
        with open(log_file, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except:
        pass
# open log window (lowkey broken dont look at this)
def open_log():
    global console_proc
    if console_proc and console_proc.poll() is None:
        return
    
    cmd = f'powershell.exe -NoExit -Command $host.ui.RawUI.WindowTitle="{LOG_TITLE}"; Get-Content "{os.path.abspath(log_file)}" -Wait'
    console_proc = subprocess.Popen(cmd, shell=True)
    time.sleep(0.3)

def close_log():
    global console_proc
    if console_proc:
        try:
            console_proc.terminate()
        except:
            pass
        console_proc = None
# force kill browsers
def kill_browsers():
    browsers = {"chrome.exe", "firefox.exe", "msedge.exe"}
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] and p.info['name'].lower() in browsers:
                p.kill()
        except:
            pass
# http bullshit
class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/ping":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
                return

            if self.path in ["/", "/index.html"]:
                try:
                    with open("index.html", encoding="utf-8") as f:
                        html = f.read()
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(html.encode())
                except:
                    self.send_error(404, "index.html not found")
                return

            super().do_GET()
        except:
            pass

    def log_message(self, *args):
        return 
# start/stop server
def start_server(event=None):
    global my_server, server_thread, space_down

    with lock:
        if space_down:
            return
        space_down = True

    write_log("=== SERVER START ===")
    start_caddy()

    try:
        socketserver.TCPServer.allow_reuse_address = True
        my_server = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), MyHandler)
    except Exception as e:
        write_log(f"Oops bind failed: {e}")
        space_down = False
        return

    server_thread = threading.Thread(target=my_server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.4)

    open_log()
    webbrowser.open("http://nikomovies.online/")
    
def stop_server(event=None):
    global my_server, space_down

    with lock:
        if not space_down:
            return
        space_down = False

    write_log("=== SERVER STOP ===")
    kill_browsers()
    stop_caddy()
    close_log()

    if my_server:
        threading.Thread(target=shutdown_server, daemon=True).start()
def shutdown_server():
    global my_server
    try:
        my_server.shutdown()
        my_server.server_close()
    except:
        pass
    my_server = None
    write_log("Server shutdown complete")

def force_exit():
    os._exit(0)

# caddy
def start_caddy():
    global caddy_proc
    if caddy_proc and caddy_proc.poll() is None:
        write_log("Caddy already running")
        return

    write_log("Starting Caddy...")
    try:
        if os.name == "nt":
            caddy_proc = subprocess.Popen(["caddy", "run"],
                                          creationflags=subprocess.CREATE_NEW_CONSOLE,
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)
        else:
            caddy_proc = subprocess.Popen(["caddy", "run"],
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL,
                                          start_new_session=True)
    except:
        write_log("Failed to start Caddy :(")

def stop_caddy():
    global caddy_proc
    write_log("Stopping Caddy...")
    for p in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            exe = (p.info["exe"] or "").lower()
            cmdline = " ".join(p.info.get("cmdline") or []).lower()
            if "caddy" in name or "caddy" in exe or cmdline.startswith("caddy"):
                write_log(f"Killing Caddy pid {p.pid}")
                p.kill()
        except:
            pass
keyboard.on_press_key("space", start_server)
keyboard.on_release_key("space", stop_server)
keyboard.add_hotkey("ctrl+shift+q", force_exit)

keyboard.wait()


