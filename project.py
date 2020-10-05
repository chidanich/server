from flask import Flask, request, abort, render_template, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import config
import json
import requests as rq
import sys
import datetime
from flask_sqlalchemy import SQLAlchemy
from oauth import OAuthSignIn
import random
import re
import os
import dicttoxml as xml
# TODO:
#       Аутентификация (OAuth 2.0) (мобильников для начала ускорить, чтоб сделали уже свою часть)
#       Push уведомления
#       тестирование ( неплохо бы найти тестировщика)
#       dashboard


app = Flask(__name__)
lm = LoginManager(app)

# mysql.init_app(app)'''
flag = False
@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    header["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,PATCH,OPTIONS"
    header["Access-Control-Allow-Credentials"] = "true"
    header["Access-Control-Allow-Headers"] = "Access-Control-Allow-Headers, Origin,Accept, X-Requested-With, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers"
    return response

# Класс SQLAlchemy с собствеными методами, не знаю зачем, захотелось написать и все
class SQLmy(SQLAlchemy):
    def add_device(self, did, rms, rgn):
        d = str(-1)
        self.session.add(Device(did=did, rooms=rms, region=rgn, sc_id=d))
        self.session.commit()
        for i in range(rms):
            nm = 'Room ' + str(i+1)
            self.session.add(DeviceRooms(did=did, name=nm))
            self.session.commit()

    def select(self, Table):
        a = []
        for i in self.session.query(Table):
            a.append(i[0])
        return a

    def select_filt(self, Table, Condition, c_val):
        a = []
        for i in self.session.query(Table).filter(Condition == c_val):
            a.append(i[0])
        return a

    def select_filt2(self, Table, Condition1, c_val1, Condition2=None, c_val2=None):
        a = []
        if Condition2 is None and c_val2 is None:
            for i in self.session.query(Table).filter(Condition1 == c_val1):
                a.append(i)
            return a
        for i in self.session.query(Table).filter(Condition1 == c_val1).filter(Condition2 == c_val2):
            a.append(i)
        return a

    def select_in(self, Table, Condition, c_val):
        a = []
        c_val = c_val + '%'
        a = self.session.query(Table).filter(Condition.like(c_val)).all()
        return a

    def select_last(self, Table, Condition, val):
        return self.session.query(Table).filter(Condition == val)[-1]

    def pop(self, Table, Condition, val):
        a = db.session.query(Table).filter(Condition == val).all()
        for i in a:
            db.session.delete(i)


db = SQLmy(app)


# ТАБЛИЦЫ БД
# Таблица User
# uid - id пользователя
# email - его почта, она же логин
class User(db.Model):
    __tablename__ = 'users'
    uid = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), nullable=False, unique=True)
    dev_us = db.relationship('DeviceUser', backref='User')



@lm.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# Таблица Device
# did - id устройства
# rooms - кол-во комнат
class Device(db.Model):
    __tablename__ = 'devices'
    did = db.Column(db.String(20), primary_key=True)
    rooms = db.Column(db.Integer)
    dev_us = db.relationship('DeviceUser', backref='Device')
    sc = db.relationship('Scen', backref='Device')
    region = db.Column(db.Integer, nullable=False)
    sc_id = db.Column(db.String(100), nullable=False)


# Таблица DeviceUser
# Связывает пользователя и устройство, а также статус пользователя (владелец, обычный пользователь)
class DeviceUser(db.Model):
    __tablename__ = 'device_users'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid'))
    did = db.Column(db.String(20), db.ForeignKey('devices.did'))
    status = db.Column(db.String(64), nullable=False)


# Таблица DeviceRooms
# Связывает устройство с комнатами (их кол-во задано в таблице Device)
class DeviceRooms(db.Model):
    __tablename__ = 'device_rooms'
    rid = db.Column(db.Integer, primary_key=True)
    did = db.Column(db.String(20), db.ForeignKey('devices.did'))
    rm = db.relationship('Room', backref='DeviceRooms')
    mm = db.relationship('Macroday', backref='DeviceRooms')
    name = db.Column(db.String(64), nullable=False)
    ch_temp = db.Column(db.Integer)
    flow = db.Column(db.Boolean)


# Таблица Room
# Хранит показатели датчиков в комнате
class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    rid = db.Column(db.Integer, db.ForeignKey('device_rooms.rid'))
    dt = db.Column(db.DateTime, nullable=False)
    temp_room = db.Column(db.Float, nullable=False)
    temp_valve = db.Column(db.Float, nullable=False)
    hum = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Float, nullable=False)
    cam = db.Column(db.Integer, nullable=False)


# Таблица Scen
# Описывает сценарии управления для устройства
class Scen(db.Model):
    __tablename__ = 'scens'
    sc_id = db.Column(db.Integer, primary_key=True)
    did = db.Column(db.String(20), db.ForeignKey('devices.did'))
    sm = db.relationship('Macroday', backref='Scen')
    name = db.Column(db.String(64), nullable=False)
    rid = db.Column(db.Integer)


# Таблица Macroday
# Описывает макродни для сценария
class Macroday(db.Model):
    __tablename__ = 'macrodays'
    mid = db.Column(db.Integer, primary_key=True)
    sc_id = db.Column(db.Integer, db.ForeignKey('scens.sc_id'))
    rid = db.Column(db.Integer, db.ForeignKey('device_rooms.rid'))
    mt = db.relationship('MdSettings', backref='Macroday')
    days = db.Column(db.String(64), nullable=False)


# Таблица MD_Settings
# Описывает макродни для сценария
class MdSettings(db.Model):
    __tablename__ = 'md_settings'
    mdid = db.Column(db.Integer, primary_key=True)
    mid = db.Column(db.Integer, db.ForeignKey('macrodays.mid'))
    time = db.Column(db.String(5), nullable=False)
    temp = db.Column(db.Float)
    hum = db.Column(db.Float)
    co2 = db.Column(db.Float)


# Таблица Climate_Devices
# Хранит названия устройств
class ClimateDevices(db.Model):
    __tablename__ = 'cl_devices'
    id_name = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(5), nullable=False)


# Таблица MD_Settings
# Описывает макродни для сценария
class DeviceSettings(db.Model):
    __tablename__ = 'dev_settings'
    ds_id = db.Column(db.Integer, primary_key=True)
    rid = db.Column(db.Integer, db.ForeignKey('device_rooms.rid'))
    id_name = db.Column(db.Integer, db.ForeignKey('cl_devices.id_name'))
    availability = db.Column(db.Boolean)
    priority = db.Column(db.Integer)
    time_beg = db.Column(db.String(5), nullable=False)
    time_end = db.Column(db.String(5), nullable=False)
    service_check = db.Column(db.Boolean)


@app.before_request
def limit_remote_addr():
    ban = ["80.85.86.175", "51.91.212.80", "185.176.221.160", "51.38.36.213", "222.186.19.221"]
    if request.remote_addr in ban:
        abort(403)  # Forbidden

# ----------------------------------------------------------
# -------------Запросы сайта _______________----------------
# ----------------------------------------------------------
@app.route("/site/get_script", methods=['GET'])  # doc
def get_script():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    cur_sc = db.select_filt(Device.sc_id, Device.did, did)[0]
    sc_id = db.select_filt(Scen.sc_id, Scen.did, did)
    sc_name = db.select_filt(Scen.name, Scen.did, did)
    a = dict(zip(sc_id, sc_name))
    a['cur'] = cur_sc
    return json.dumps(a)


@app.route("/site/del_script", methods=['GET'])  # doc
def del_script():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    sc_id = request.args.get('sc_id', type=int)
    if sc_id is None:
        return "No script id send"
    if db.select_filt(Scen.did, Scen.sc_id, sc_id)[0] != did:
        return 'Script ID not found'
    md = db.select_filt(Macroday.mid, Macroday.sc_id, sc_id)
    for i in md:
        db.pop(MdSettings, MdSettings.mid, i)
    db.pop(Macroday, Macroday.sc_id, sc_id)
    db.pop(Scen, Scen.sc_id, sc_id)
    db.session.commit()
    a = db.select_filt2(Device, Device.did, did)[0]
    if int(a.sc_id) == int(sc_id):
        a.sc_id = -1
    db.session.commit()

    return '200'


@app.route("/site/apapt", methods=['POST'])  # doc
def adapt():
    site_sets = dict(request.get_json())

    # Создание сценария
    did = site_sets['did']
    sc_name = site_sets['sc_name']
    db.session.add(Scen(did=did, name=sc_name))
    db.session.commit()
    sc_id = db.select_last(Scen.sc_id, Scen.did, did)[0]
    print(sc_id)
    # Создание макродней
    m_days = {}
    for i in site_sets.keys():
        if i == 'did' or i == 'sc_name':
            continue
        macrodays = ''
        for j in dict(site_sets[i]).keys():
            macrodays = macrodays + '_' + j
        m_days[i] = macrodays[1:]
    params = {}
    k = 0
    for i in m_days.keys():
        params['rid_' + str(k)] = i
        params['days_' + str(k)] = m_days[i]
        k += 1

    db.pop(Macroday, Macroday.sc_id, sc_id)
    db.session.commit()

    room_num = db.select_filt(Device.rooms, Device.did, did)[0]
    for i in range(room_num):
        rid = params['rid_' + str(i)]
        days = params['days_' + str(i)].split('_')
        for d in days:
            db.session.add(Macroday(sc_id=sc_id, rid=rid, days=d))
    db.session.commit()
    a = list(
        zip(db.select_filt(Macroday.rid, Macroday.sc_id, sc_id), db.select_filt(Macroday.days, Macroday.sc_id, sc_id)))
    md = dict(zip(db.select_filt(Macroday.mid, Macroday.sc_id, sc_id), a))
    print(md)
    sets = {}

    def get_key(mcd, rd):
        for k, v in md.items():
            if (str(mcd) in v) and (int(rd) in v):
                return k
    k = 0
    for i in site_sets.keys():
        if i == 'did' or i == 'sc_name':
            continue
        temp1 = {}
        temp1['rid'] = i
        v = 0
        for j in dict(site_sets[i]).keys():
            temp2 = {}
            temp2['mid'] = get_key(j, i)
            for l in dict(site_sets[i][j]).keys():
                temp2[l] = site_sets[i][j][l]
            temp1['mid_' + str(v)] = temp2
            v += 1
        sets['rid_' + str(k)] = temp1
        k += 1
    sets['did'] = did

    for i in range(room_num):
        cur_room = 'rid_' + str(i)
        mdays_num = len(sets[cur_room]) - 1
        for j in range(mdays_num):
            cur_mid = 'mid_' + str(j)
            mid = sets[cur_room][cur_mid]['mid']
            db.pop(MdSettings, MdSettings.mid, mid)
            sets_num = len(sets[cur_room][cur_mid]) - 1
            for k in range(sets_num):
                cur_set = 'set_' + str(k)
                time = sets[cur_room][cur_mid][cur_set]["time"]
                time = time.replace('-', ':')
                temp = sets[cur_room][cur_mid][cur_set]["temp"]
                hum = sets[cur_room][cur_mid][cur_set]["hum"]
                co = sets[cur_room][cur_mid][cur_set]["co"]

                db.session.add(MdSettings(mid=mid, time=time, temp=temp, hum=hum, co2=co))
    db.session.commit()
    return '200'


@app.route("/site/rm_config", methods=['GET'])  # doc
def rm_cnfg():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    cnfg = db.select_filt2(DeviceRooms, DeviceRooms.did, did)
    conf = {}
    conf['did'] = did
    for i in range(len(cnfg)):
        conf['r_' + str(i)] = {}
        conf['r_' + str(i)]['rid'] = cnfg[i].rid
        conf['r_' + str(i)]['r_name'] = cnfg[i].name
    return json.dumps(conf)


@app.route("/site/timezone", methods=['GET'])  # doc
def timezone():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    reg = request.args.get('reg', type=str)
    if reg is None:
        reg = db.select_filt(Device.region, Device.did, did)[0]
        return str(reg)
    rgn = db.select_filt2(Device, Device.did, did)[0]
    rgn.region = reg
    db.session.commit()
    return '200'


@app.route("/site/rm_nm", methods=['GET'])  # doc
def rnm():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rid = request.args.get('rid', type=str)
    rname = request.args.get('rname', type=str)
    a = db.select_filt2(DeviceRooms, DeviceRooms.did, did, DeviceRooms.rid, rid)[0]
    a.name = rname
    db.session.commit()
    return '200'


# ----------------------------------------------------------
# -------------Запросы мобильного приложения----------------
# ----------------------------------------------------------
# Запрос покзателей датчиков
@app.route("/app/datchik", methods=['GET'])  # doc
def ask_dat():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rooms = db.select_filt(DeviceRooms.rid, DeviceRooms.did, did)
    sensors = {}
    for i in range(len(rooms)):
        a = db.select_last(Room, Room.rid, rooms[i])
        sensors[str(rooms[i])] = [str(a.dt), a.temp_room, a.temp_valve, a.hum, a.co2, a.cam]
    return json.dumps(sensors)


@app.route("/app/device_settings", methods=['GET'])
def ask_dat():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'

    rid = request.args.get('rid', type=int)
    id_name = request.args.get('id_name', type=int)
    availability = request.args.get('aval', type=int)
    priority = request.args.get('prior', type=int)
    time_beg = request.args.get('time_beg', type=str)
    time_end = request.args.get('time_end', type=str)
    service_check = request.args.get('serv', type=int)
    ds_i = request.args.get('ds_id', type=int)

    if ds_i is None:
        new_dev = DeviceSettings(rid=rid, id_name=id_name, availability=availability, priority=priority,
                                      time_beg=time_beg, time_end=time_end, service_check=service_check)
        db.session.add(new_dev)
        db.session.commit()
        ds_i = new_dev.ds_id
        return ds_i
    old_dev = db.select_filt(DeviceSettings, DeviceSettings.ds_id, ds_i)
    old_dev.rid = rid
    old_dev.availability = availability
    old_dev.priority = priority
    old_dev.time_beg = time_beg
    old_dev.time_end = time_end
    old_dev.service_check = service_check
    return "200"

# Запрос статистики за день
@app.route("/app/stat", methods=['GET'])  # doc
def stat():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rid = request.args.get('rid', type=int)
    dt = request.args.get('dt', type=str)
    if dt is None:
        return "No date send"
    a = db.select_filt2(Room, Room.rid, rid)
    b = []
    for i in range(len(a)):
        if dt == str(a[i].dt)[:-9]:
            b.append(a[i])
    stat = {}
    for i in b:
        stat[str(i.dt)] = [i.temp_room, i.temp_valve, i.hum, i.co2, i.cam]
    return json.dumps(stat)


# Настройки (текущий сценарий)
@app.route("/app/settings", methods=['GET'])  # doc
def stngs():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    sc_id = request.args.get('sc_id', type=int)
    if sc_id is None:
        sc_id = -1
    # region = request.args.get('region', type=int)
    a = db.session.query(Device).filter(Device.did == did)[0]
    a.sc_id = sc_id
    db.session.add(a)
    db.session.commit()
    return '200'


@app.route("/app/scen/get_cur", methods=['GET'])  # doc
def get_cur():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    sc_id = db.select_filt(Device.sc_id, Device.did, did)[0]
    reg = db.select_filt(Device.region, Device.did, did)[0]
    if int(sc_id) == -1:
        return "-1"
    a = {}
    cur_time = str((datetime.datetime.now() + datetime.timedelta(hours=reg - 3)).now())[:-10]
    cur_time = int(cur_time[:2])*60 + int(cur_time[-2:])
    cur_weekday = (datetime.datetime.now() + datetime.timedelta(hours=reg - 3)).weekday()
    rid = request.args.get('rid', type=int)
    macrodays = db.select_filt2(Macroday, Macroday.sc_id, sc_id, Macroday.rid, rid)
    cur_md = None
    for md in macrodays:
        if str(cur_weekday) in md.days:
            cur_md = md.mid
    sets = db.select_filt2(MdSettings, MdSettings.mid, cur_md)
    if cur_md is None:
        return json.dumps([None, None, None])
    temp = []
    for s in sets:
        tm = int(s.time[:2])*60 + int(s.time[-2:])
        diff = cur_time - tm
        if diff < 0:
            continue
        temp.append([diff, s])
    tmin = temp[0][0]
    min = temp[0][1]
    for i in range(1, len(temp)):
        if temp[i][0] < tmin:
            tmin = temp[i][0]
            min = temp[i][1]
    return json.dumps([min.temp, min.hum, min.co2])


@app.route("/app/ch_temp", methods=['GET'])  # doc
def ch_temp():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rid = request.args.get('rid', type=int)
    ch_temp = request.args.get('temp', type=int)
    rm = db.select_filt2(DeviceRooms, DeviceRooms.did, did, DeviceRooms.rid, rid)[0]
    rm.ch_temp = ch_temp
    db.session.commit()
    return '200'


@app.route("/app/flow", methods=['GET'])  # doc
def flow():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rid = request.args.get('rid', type=int)
    rm = db.select_filt2(DeviceRooms, DeviceRooms.did, did, DeviceRooms.rid, rid)[0]
    rm.flow = True
    db.session.commit()
    return '200'


# -------------------------------------------------------------
# --------------------Запросы устройства-----------------------
# -------------------------------------------------------------
# Отправка показателей датчиков с устройства
@app.route("/dev/datchik", methods=['GET'])  # doc
def datchik():

    did = request.args.get('did', type=str)
    if did is None:
        return 'You must send device ID'
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    room_num = db.select_filt(Device.rooms, Device.did, did)[0]
    reg = db.select_filt(Device.region, Device.did, did)[0]
    rtr = str(db.select_filt(Device.sc_id, Device.did, did)[0])
    for i in range(room_num):
        rid = request.args.get('rid_' + str(i), type=int)
        rtr = rtr + '_' + str(rid)
        tmp = db.select_filt2(DeviceRooms, DeviceRooms.did, did, DeviceRooms.rid, rid)[0]
        rtr = rtr + '_' + str(tmp.ch_temp) + '_' + str(tmp.flow)
        tmp.ch_temp = None
        tmp.flow = None
        temp_room = request.args.get('tr_' + str(i), type=float)
        if temp_room is None:
            temp_room = 0
        temp_valve = request.args.get('tv_' + str(i), type=float)
        if temp_valve is None:
            temp_valve = 0
        hum = request.args.get('hum_' + str(i), type=float)
        if hum is None:
            hum = 0
        co2 = request.args.get('co_' + str(i), type=float)
        if co2 is None:
            co2 = 0
        cam = request.args.get('cam_' + str(i), type=int)
        if cam is None:
            cam = 0
        dt = datetime.datetime.now() + datetime.timedelta(hours=reg-3)
        db.session.add(Room(rid=rid, dt=dt, temp_room=temp_room, temp_valve=temp_valve, hum=hum, co2=co2, cam=cam))
    db.session.commit()

    return rtr


@app.route("/dev/scen", methods=['GET'])  # doc
def dev_scen():
    did = request.args.get('did', type=str)
    if did is None:
        return 'You must send device ID'
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    sc_id = db.select_filt(Device.sc_id, Device.did, did)[0]
    script = {}
    script["sc_id"] = sc_id
    rid1 = db.select_filt(DeviceRooms.rid, DeviceRooms.did, did)
    c = db.select_filt(Macroday.mid, Macroday.sc_id, sc_id)
    for i in db.session.query(MdSettings).filter(MdSettings.mid.in_(c)):
        sc = db.select_filt(Macroday.sc_id, Macroday.mid, i.mid)[0]
        if str(sc) != str(sc_id):
            continue
        days = str(db.select_filt(Macroday.days, Macroday.mid, i.mid)[0])
        time = str(i.time)
        temp = str(i.temp)
        hum = str(i.hum)
        co2 = str(i.co2)
        rid = str(db.select_filt(Macroday.rid, Macroday.mid, i.mid)[0])
        if rid not in script:
            script[rid] = {}
        if days not in script[rid]:
            script[rid][days] = {}
        script[rid][days][time] = [temp, hum, co2]
    type = request.args.get('type', type=str)
    if type == "json":
        return json.dumps(script)
    return xml.dicttoxml(script)


@app.route("/dev/devices", methods=['GET'])
def ask_dat():
    did = request.args.get('did', type=str)
    if did is None:
        return "No device id send"
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    rooms = db.select_filt(DeviceRooms.rid, DeviceRooms.did, did)
    devices = {}
    for i in range(len(rooms)):
        a = db.select_last(DeviceSettings, DeviceSettings.rid, rooms[i])
        devices[str(rooms[i])] = [str(a.ds_id), str(a.rid), str(a.availability), str(a.priority), str(a.time_beg),
                                  str(a.time_end), str(a.service_check)]
    return json.dumps(devices)


@app.route("/dev/sync_time", methods=['GET'])  # doc
def sync_time():
    did = request.args.get('did', type=str)
    if did is None:
        return 'You must send device ID'
    if len(db.select_filt(Device.did, Device.did, did)) == 0:
        return 'Device ID not found'
    reg = db.select_filt(Device.region, Device.did, did)[0]
    dt = datetime.datetime.now() + datetime.timedelta(hours=reg - 3)
    return str(dt)[:-7]


# -------------------------------------------------------------
# -------Запросы общие (для проверки работоспособности)--------
# -------------------------------------------------------------
@app.route("/ok", methods=['GET'])
def checkStatus():
    return "OK"


@app.route("/<username>", methods=['GET'])
def index1(username):
    return "Hello, %s!" % username

# -------------------------------------------------------------
# ----------------Запросы для разработчика---------------------
# -------------------------------------------------------------
@app.route("/development", methods=['GET'])
def index():
    print(str(current_user.is_anonymous), file=sys.stderr)
    if current_user.is_anonymous:
        return redirect(url_for('oauth_authorize', provider='yandex'))
    return render_template('index.html')

# Регистрация нового устройства
@app.route("/development/register", methods=['GET'])  #doc
def reg_dev():
    def gen_id():
        symbs = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'z',
                 'x', 'c', 'v', 'b', 'n', 'm', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', 'A', 'S', 'D', 'F',
                 'G', 'H', 'J', 'K', 'L', 'Z', 'X', 'C', 'V', 'B', 'N', 'M']
        did = ''
        for i in range(20):
            did = did + random.choice(symbs)
        return did
    did = request.args.get('did', type=str)
    if did is None:
        ids = db.select(Device.did)
        idd = gen_id()
        while idd in ids:
            idd = gen_id()
    else:
        idd = did
    region = request.args.get('region', type=int)
    rooms = request.args.get('rooms', type=int)
    db.add_device(idd, rooms, region)
    rms = db.select_filt(DeviceRooms.rid, DeviceRooms.did, idd)
    output = str(idd)
    for i in enumerate(rms):
        output = output + '|' + str(i[1])
    return output

# Логи
@app.route("/development/log",  methods=['GET'])
def loging():
    f = open('ll.txt', 'r')
    l = []
    k = []
    start = end = 0
    for line in f:
        k.append(line)
    k.reverse()
    start = end = 0
    for line in k:
        if "[pid" in line:
            end += 1
            result0 = re.search("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", line)
            result1 = re.search("\[(...........)[0-9]{2}\:[0-9]{2}\:[0-9]{2}(.....)\]\s\S*\s\S*", line)
            sp = ''
            for i in range(len('173.212.199.138')-len(result0.group(0))):
                sp = sp + '  '
            res = 'REQ:        ' + result0.group(0) + '    ' + sp + result1.group(0)
            l.append(res)
        else:
            k = []
            l.append(line)

    return render_template("log.html", l=l)
# -------------------------------------------------------------
# -------------------------Авторизация-------------------------
# -------------------------------------------------------------
@app.route('/logout')
def logout():
    logout_user()
    print(str(current_user.is_anonymous), file=sys.stderr)
    return redirect(url_for('logn'))


@app.route('/logn')
def logn():
    return render_template('login.html')

@app.route('/is_auth')
def is_auth():
    return str(not current_user.is_anonymous)


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    logout_user()
    print(str(current_user.is_anonymous), file=sys.stderr)
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    email = oauth.callback()
    if email is None:
        flash('Authentication failed.')
        return redirect(url_for('logn'))
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    print('++' + user.email, file=sys.stderr, )
    login_user(user, True)
    print(current_user.email, file=sys.stderr, )
    return redirect(url_for('index'))


# Точка входа входа на запуск сервера
if __name__ == "__main__":
    print("\nStarted:" + str(datetime.datetime.now())[:-7], file=sys.stderr)
    app.run(host='0.0.0.0', debug=True)





