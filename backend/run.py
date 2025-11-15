from app import app, init_keys
if __name__ == "__main__":
    init_keys()
    app.run(host="0.0.0.0", port=5000, debug=True)