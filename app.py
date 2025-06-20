from flask import Flask
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# Blueprint 등록
from gongji import gongji_bp
from menu import lunch_bp, dinner_bp, anju_bp
from dice import soju_bp, dice_bp

app.register_blueprint(gongji_bp)
app.register_blueprint(lunch_bp)
app.register_blueprint(dinner_bp)
app.register_blueprint(anju_bp)
app.register_blueprint(soju_bp)
app.register_blueprint(dice_bp)

# 서버 실행
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
