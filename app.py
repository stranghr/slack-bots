from flask import Flask
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# Blueprint 등록
from routes.gongji import gongji_bp
from routes.menu import lunch_bp, dinner_bp, anju_bp
from routes.dice import soju_bp, dice_bp  # dice_bp도 따로 있다면 함께
from routes.notice import noticesc_bp
from routes.weather import weather_bp

app.register_blueprint(noticesc_bp)
app.register_blueprint(gongji_bp)
app.register_blueprint(lunch_bp)
app.register_blueprint(dinner_bp)
app.register_blueprint(anju_bp)
app.register_blueprint(soju_bp)
app.register_blueprint(dice_bp)
app.register_blueprint(weather_bp)

# 서버 실행
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
