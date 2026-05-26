from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test')
def test_api():
    return jsonify({
        "status": "success",
        "message": "Selamat! Backend API berbasis Flask sudah terhubung."
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
