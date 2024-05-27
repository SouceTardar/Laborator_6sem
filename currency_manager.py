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

# Добавление валюты
@app.route("/load", methods=["POST"])
def load_currency():
    cur = conn.cursor()

    data = request.json
    currency_name = data["currency_name"]
    rate = data.get("rate")

    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
    result = cur.fetchone()

    if result:
        cur.close()
        return jsonify({"error": "Валюта уже существует в базе данных"}), 400

    conn.commit()

    cur.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (currency_name, rate))
    conn.commit()
    cur.close()

    return jsonify({"status": "Валюта успешно добавлена"}), 200

# Изменение валюты
@app.route("/update_currency", methods=["POST"])
def update_currency():
    cur = conn.cursor()

    data = request.json
    currency_name = data["currency_name"]
    rate = data["rate"]

    cur.execute("SELECT * FROM currencies WHERE currency_name=%s", (currency_name,))
    result = cur.fetchone()

    if not result:
        return jsonify({"error": "Валюта не найдена в базе данных"}), 400

    cur.execute("UPDATE currencies SET rate=%s WHERE currency_name=%s", (rate, currency_name))
    conn.commit()
    cur.close()

    return jsonify({"status": "OK"}), 200

# Удаление валюты
@app.route("/delete", methods=["POST"])
def delete_currency():
    cur = conn.cursor()

    data = request.json
    currency_name = data["currency_name"]

    cur.execute("SELECT * FROM currencies WHERE currency_name=%s", (currency_name,))
    result = cur.fetchone()
    if not result:
        return jsonify({"Такая валюта отсутствует в списке"}), 400

    cur.execute("DELETE FROM currencies WHERE currency_name=%s", (currency_name,))
    conn.commit()

    return jsonify({"status": "OK"}), 200


if __name__ == '__main__':
    app.run(port=5001, debug=True)
