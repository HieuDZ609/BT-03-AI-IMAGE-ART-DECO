from http.server import HTTPServer, BaseHTTPRequestHandler

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            body = """# HELP images_total Total images processed
# TYPE images_total gauge
images_total 100
# HELP jobs_total Total jobs processed
# TYPE jobs_total gauge
jobs_total 50
"""
            self.wfile.write(body.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/generate':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response_body = '{"status": "success", "job_id": "job_123456", "message": "Image generation task created"}'
            self.wfile.write(response_body.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), MetricsHandler)
    print("Mock Gateway running on port 8000...")
    server.serve_forever()
def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            body = """# HELP images_total Total images processed
# TYPE images_total gauge
images_total 100
# HELP jobs_total Total jobs processed
# TYPE jobs_total gauge
jobs_total 50
"""
            self.wfile.write(body.encode('utf-8'))
        elif self.path.startswith('/result/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            # Giả lập trả về đường dẫn tới ảnh kết quả
            response_body = '{"status": "completed", "image_url": "https://picsum.photos/512/512", "message": "Image generated successfully"}'
            self.wfile.write(response_body.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
