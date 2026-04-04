from flask import Flask, jsonify

app = Flask(__name__)

@app.before_request
def crash():
    raise Exception("Boom!")

@app.errorhandler(500)
def err(e):
    return jsonify(error=str(e)), 500

@app.route("/health")
def h():
    return "ok"

if __name__ == '__main__':
    with app.test_client() as c:
        try:
            print(c.get("/health").status_code)
        except Exception as e:
            print("Crashed:", e)
