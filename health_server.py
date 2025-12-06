#!/usr/bin/env python3
"""
Simple HTTP health check server for Shipyard routing.
Runs alongside the Kafka consumer to provide a health endpoint.
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import json

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health' or self.path == '/':
            # Check basic health
            health_status = {
                "status": "healthy",
                "service": "series-consumer",
                "version": "1.0.0"
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass

def start_health_server(port=8080):
    """Start the health check HTTP server in a background thread."""
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"✅ Health check server started on port {port}")
        return server
    except Exception as e:
        print(f"⚠️  Could not start health server: {e}")
        return None

if __name__ == "__main__":
    # Run standalone for testing
    port = int(os.getenv('HEALTH_PORT', '8080'))
    print(f"Starting health check server on port {port}...")
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health check server running on http://0.0.0.0:{port}/health")
    server.serve_forever()

