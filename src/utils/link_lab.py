import json
import os
import http.server
import socketserver
import webbrowser
from functools import partial
import yaml

# Minimal backend to serve the UI and handle the "Save" action
class LabHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            filename = data.get('filename', 'new_workflow.yaml')
            manifest = data.get('manifest')
            
            # Save the YAML
            save_path = os.path.join('..', 'workflows', filename)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(manifest, f, sort_keys=False)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'path': save_path}).encode())
        
        elif self.path == '/load':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            json_path = data.get('path')
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'workflow': workflow}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())

def run_lab():
    PORT = 8055
    # Change directory to the utils folder to serve the UI
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    Handler = LabHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 Link Lab is running at http://localhost:{PORT}")
        print("Opening browser...")
        webbrowser.open(f"http://localhost:{PORT}/link_lab_ui.html")
        httpd.serve_forever()

if __name__ == "__main__":
    run_lab()
