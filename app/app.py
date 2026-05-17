from flask import Flask
from config import SECRET_KEY
from database import init_db
from mqtt.mqtt_handler import start_mqtt
from routes.api import api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(api_bp)

if __name__ == "__main__":
    init_db()
    start_mqtt()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)