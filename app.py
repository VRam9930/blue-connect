from flask import Flask
from whatsapp.bot import whatsapp_bp
from dotenv import load_dotenv
import config

load_dotenv()

app = Flask(__name__)
app.register_blueprint(whatsapp_bp)

@app.route("/")
def home():
    return "Blue Connect WhatsApp Bot is Running 🚜"

if __name__ == "__main__":
    app.run()

