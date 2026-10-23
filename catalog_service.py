import argparse
import math
from datetime import datetime, timezone
import threading

from flask import Flask, jsonify, request
app = Flask(__name__)

products = {}
next_product_id = 1
products_lock = threading.Lock()


def utc_now():
    # return an ISO 8601 timestamp with an explicit UTC offset
    return datetime.now(timezone.utc).isoformat()

def normalize_price(value):
    # validate a positive price and keep whole-number prices as integers
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0: return None
    if isinstance(value, float) and not math.isfinite(value): return None
    normalized = value if isinstance(value, int) else round(value, 2)
    return normalized if normalized > 0 else None

@app.errorhandler(404)
def handle_route_not_found(_error):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(405)
def handle_method_not_allowed(_error):
    return jsonify({"error": "Method not allowed"}), 405

@app.get("/health")
def health():
    return jsonify({"service": "catalog", "status": "ok"}), 200

@app.post("/products")
def create_product():
    global next_product_id

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    name = data.get("name")
    price = normalize_price(data.get("price"))
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Field 'name' must be a non-empty string"}), 400
    if price is None:
        return jsonify({"error": "Field 'price' must be a positive number"}), 400

    # id generation and dictionary update form one critical section
    # only one request thread may execute it at a time.
    with products_lock:
        product = {"id": next_product_id, "name": name.strip(), "price": price, "created_at": utc_now(),}
        products[next_product_id] = product
        next_product_id += 1
    return jsonify(product), 201

@app.get("/products/<int:product_id>")
def get_product(product_id):
    with products_lock:
        product = products.get(product_id)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product), 200

def parse_arguments():
    parser = argparse.ArgumentParser(description="Lab 3 Catalog service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    return parser.parse_args()

def main():
    args = parse_arguments()
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535")
    # threaded=True lets Flask handle independent requests concurrently.
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
