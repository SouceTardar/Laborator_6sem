from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(dbname="bot_lab", user="maxim_dlia_bota",
                        password="shtangauer05", host="127.0.0.1")
cur = conn.cursor()

@app.route('/convert', methods=['GET'])
def convert_currency():
    cur = conn.cursor()

    data = request.json
    currency_name = data.get('currency_name')
    amount = data.get('amount')

    cur.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
    result = cur.fetchone()

    if result:
        rate = result[0]
        converted_amount = float(amount) * float(rate)
        return jsonify({'converted_amount': converted_amount}), 200
    else:
        return jsonify({"error": 'Указанной валюты нет в списке. Пожалуйста, выберите из доступных валют'}), 400


@app.route('/currencies', methods=['GET'])
def get_currencies():
    cur = conn.cursor()
    cur.execute('SELECT * FROM currencies')
    currencies = cur.fetchall()
    conn.close()
    return jsonify({'currencies': currencies})


if __name__ == "__main__":
    app.run(port=5002)
