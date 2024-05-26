from flask import Flask, request, jsonify
import psycopg2
import os
from aiogram import Router

app = Flask(__name__)

# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(dbname="bot_lab", user="maxim_dlia_bota",
                        password="shtangauer05", host="127.0.0.1")

bot_token = os.getenv('TOKEN')
router = Router()

# Проверка пользователя
@app.route("/check_admin", methods=["POST"])
def check_admin():
    cur = conn.cursor()

    chat_id = (request.json["chat_id"],)

    cur.execute("SELECT EXISTS(SELECT 1 FROM admins WHERE chat_id = %s)", chat_id)
    result = cur.fetchone()[0]

    cur.close()

    return jsonify({"is_admin": result}), 200




if __name__ == '__main__':
    app.run(port=5003, debug=True)