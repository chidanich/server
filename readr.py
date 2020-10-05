import requests
from flask import Flask, request
'''
Сервер для переадресации запросов
ждем когда Саня научится делать https запросы нормально -_-
'''
app = Flask(__name__)
@app.route("/dev/datchik", methods=['GET'])
def askdt():
    a = dict(request.args)
    b = requests.get("https://vc-srvr.ru/dev/datchik", params=a)
    return str(b.text)


@app.route("/dev/scen", methods=['GET'])
def scn():
    a = dict(request.args)
    b = requests.get("https://vc-srvr.ru/dev/scen", params=a)
    return str(b.text)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)