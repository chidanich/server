from flask import Flask, request, jsonify
from flask import render_template
import requests as rq
import sys
import datetime
import config

'''
Сервер раньше юзался для логов и презентации на постерной сессии.
Сейчас не используется, но пусть будет на всякий случай
'''
app = Flask(__name__)


datch = [[0.0, 0.0, 0.0], [0, 0]]


def ventilation(person):
    productivity = 30 * int(person) # требуемая производительность (воздухообмен, м3/ч)
    rotates = 23*productivity - 0.19 # обороты в минуту
    time = productivity * 60 / 98 # выражается в минутах. Константа в знаменателе - производительность нашего вентилятора. Можно завести переменную для солидности.
    return productivity, rotates, round(time)


@app.route("/gt", methods=['GET'])
def gt():
    productivity, rotates, time = ventilation(datch[1][0])
    temp = datch[0][0]
    hum = datch[0][1]
    co = datch[0][2]
    fir = datch[1][0]
    sec = datch[1][1]
    if int(datch[1][0]) == 0:
        v = 0
    elif int(datch[1][0]) == 1:
        v = 2.5
    elif int(datch[1][0]) == 2:
        v = 1.4
    elif int(datch[1][0]) == 3:
        v = 0.8
    elif int(datch[1][0]) == 4:
        v = 0.5
    elif int(datch[1][0]) == 5:
        v = 0.4
    else:
        v = 0.2
    return productivity, rotates, time, temp, hum, co, fir, sec, v



@app.route("/", methods=['GET'])
def index():
    try:
        response = rq.get(IP + ':' + PORT_MAIN + '/ok')
        status = "WORKING"
    except rq.exceptions.ConnectionError:
        status = "DOWN"

    if int(datch[1][0]) == 0:
        v = 0
    elif int(datch[1][0]) == 1:
        v = 2.5
    elif int(datch[1][0]) == 2:
        v = 1.4
    elif int(datch[1][0]) == 3:
        v = 0.8
    elif int(datch[1][0]) == 4:
        v = 0.5
    elif int(datch[1][0]) == 5:
        v = 0.4
    else:
        v = 0.2
    print(datch[1][0], file=sys.stderr)
    print(v, file=sys.stderr)
    productivity, rotates, time = ventilation(datch[1][0])
    return render_template("index.html", status=status, temp=datch[0][0], hum=datch[0][1], co=datch[0][2],
                           fir=datch[1][0], sec=datch[1][1], prd=productivity, rts=rotates, tm=time, v=v)


@app.route("/data", methods=['POST'])
def getData():
    dat = request.get_json()
    datch[0] = dat
    return "200"


@app.route("/data1", methods=['POST'])
def getDat1a():
    dat = request.get_json()
    datch[1] = dat
    return "2001"


@app.route("/log", methods=['GET'])
def loging():
    f = open('server/log.txt', 'r')
    l = []
    k = []
    start = end = 0
    for line in f:
        k.append(line)
    k.reverse()
    print(k)
    print(len(k))
    for line in k:
        end += 1
        if "Started:" in line:
            l.append("\n\n")
            l.append(line)
            for i in range(start, end-1):
                l.append(k[i])
                start = end
    return render_template("log.html", l=l)


@app.route("/dlog", methods=['GET'])
def dloging():
    f = open('server/llog.txt', 'r')
    l = []
    k = []
    start = end = 0
    for line in f:
        k.append(line)
    k.reverse()
    print(k)
    print(len(k))
    for line in k:
        end += 1
        if "Started:" in line:
            l.append("\n\n")
            l.append(line)
            for i in range(start, end-1):
                l.append(k[i])
                start = end
    return render_template("log.html", l=l)


if __name__ == "__main__":
    print("\nStarted:" + str(datetime.datetime.now())[:-7], file=sys.stderr)
    app.run(host='0.0.0.0', port=PORT)

