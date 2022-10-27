""" eltako_home.py

    Simple Eltako Home automation using Func Series 14
    https://www.eltako.com/fileadmin/downloads/en/_main_catalogue/Gesamt-Katalog_ChT_gb_highRes.pdf
    FAM14 (pos 4)  FTS14EM, FUD14, FSR14  FSB14

    Version Date  Author	Comment
    V1.00 2020-12-09 LH     initial
"""
import os
import time
import json
import argparse
import copy
import serial
import datetime
import threading
import queue
import uvicorn
from starlette.staticfiles import StaticFiles
from fastapi import FastAPI, Query, Body, APIRouter
from typing import Dict

VERSION = "0.0.1"
AUTHOR = "(c) 2021 LuHe"
APPNAME = "El-tako Home"
DEBUG = False

ini = {
    "HTTP_PORT": 8088,
    "STATIC_DIR": "../www",
    "API_BASE": "/tako-home/api",
    "COM_PORT": "COM7:38400,n,8,1"
}
tako = {}
qmsg = queue.Queue()


def str_2hex(data):
    if not data: return ''
    if type(data) == bytes:
        return '.'.join([('%02X' % o) for o in data])
    return '.'.join([('%02X' % ord(o)) for o in data])


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def dbg(head, data=''):
    print(f'{now()} {head} {str_2hex(data)}')


def log(*pars):
    print(now(), repr(pars))


def err(*pars):
    log('ERROR', pars)


def task_start(ttask, args=()):
    """ start a thread """
    t = threading.Thread(target=ttask, args=args)
    t.daemon = True
    t.start()


# ---------- SERIAL STUFF ----------
def ser_open(comx=None, time_out=None):
    if comx is None:
        comx = 'COM3:38400,n,8,1'
    if time_out is None:
        time_out = 0.1
    baud = 115200
    party = 'N'
    bits = 8
    stop = 1
    com = comx.split(':')
    if len(com)>1:
        pbs = com[1].split(',')
        baud = int(pbs[0])
        if len(pbs) > 1:    party = pbs[1].upper()
        if len(pbs) > 2:    bits = int(pbs[2])
        if len(pbs) > 3:    stop = int(pbs[3])
    print('open %s:%s,%s,%s,%s' % (com[0], baud, party, bits, stop))
    # print(repr(com_baud))
    ser = serial.Serial(port=com[0], baudrate=baud, bytesize=bits, parity=party, stopbits=stop,
                        timeout=time_out, xonxoff=0, rtscts=0, write_timeout=5)
    return ser


def ser_write(ser, data):
    dbg('-> ', data)
    ser.write(data)


def ser_read(ser, buff):
    data = ser.read(128)
    if type(data) == str:  # python 2.6
        data = bytes(data)
    if len(data) > 0:
        buff += data
    return buff


# ----------- ELTAKO STUFF ------------------
SYNC = b'\xA5\x5A'


def packet(data=b'\x00\x00\x00\x00', addr=b'\x00\x00\x00\x00', status=0x30, org=5, hseq=0):
    """ packet enocean ESP2
        0  1    2     3       4  5  6  7   8  9  10 11     12     13
        A5 5A   0B    05     50 00 00 00   FE FE E2 0E     30     7C
        PRE   | LEN | RORG |     DATA    |    SOURCE   | STATUS | CSUM
    """
    data += addr + bytes([status])
    hlen = (len(data) + 2) | (hseq << 5)
    data = bytes([hlen, org]) + data
    pack = SYNC + data + bytes([sum(data) % 256])
    return pack


def packet_fnd(buff):
    p = buff.find(SYNC)
    if p >= 0:
        buff = buff[p:]
    else:
        buff = b''
    if len(buff) < 14:
        return None, buff
    pack = buff[:14]
    buff = buff[14:]
    cs = sum(pack[2:13]) % 256
    if cs != pack[13]:
        log('ERROR csum: ', pack)
    elif pack[3:12] == b'\xfc' + b'\x00' * 8:
        print(f"%02x {(pack[12]%8)*'.'}    \r" % pack[12], end="", flush=True)
    else:
        if DEBUG:
            dbg('<- ', pack)
        pack_2tako(pack)
    return pack, buff


def pack_2tako(pack):
    global tako
    if pack[2] != 0x8b:
        return
    addr = pack[8:12].hex()
    if addr in tako:
        tako[addr]['data'] = pack[4:8].hex()


def to_4byte(a):
    if isinstance(a, str):  # a is string
        a = bytes.fromhex(a)
    if not isinstance(a, (bytes, bytearray)):   # a is number
        a = a.to_bytes(4, 'big')
    if len(a) >= 4:
        return a[-4:]
    return b'\x00' * (4-len(a)) + a


def snd_button(addr=b'\x00\x00\x10\x23', data='\x30\x00\x00\x00'):
    d = to_4byte(data)
    return packet(d, addr=to_4byte(addr), status=0x30 if d[0] else 0x20)


# Background polling task
def tako_run():
    ser = None
    buff = b''
    cnt = 0
    while 1:
        try:
            if ser is None:
                time.sleep(1)
                ser = ser_open(ini['COM_PORT'])
                time.sleep(0.5)
                ser_write(ser, packet(org=0xff, status=0x00))
                continue
            buff = ser_read(ser, buff)
            d, buff = packet_fnd(buff)
            if not qmsg.empty():
                ev = qmsg.get()  # wait for a message
                ser_write(ser, snd_button(ev['addr'], ev['data']))
        except serial.SerialException as e:
            err('serial:', e)
            try:
                ser.close()
            except:
                pass
            ser = None
        except Exception as e:
            err('serial:', e)


# --------------- WEB service --------------
route_hub = APIRouter()


@route_hub.get("/read", tags=["tags"], summary="read all takos")
async def tags_rd(description="read all takos"):
    tres = {}
    for tak in tako:
        tk = tako[tak]
        data = tk.get('data', "00000000")
        dik = {}
        if tk['typ'] == 'FUD14':
            dik = {'on': 1 if data[6:9] == '09' else 0}
            dik['dim'] = int(data[2:4], 16)
        else:
            dik = {'on': 1 if data[0:2] == '70' else 0}
        gr = tk['group']
        if gr in tres:
            tres[gr][tk['name']] = dik
        else:
            tres[gr] = {tk['name']: dik}
    return tres


@route_hub.put("/write", tags=["tags"], summary="write tags")
async def tags_wr(tags: Dict = Body(..., description="{group.name: 1}", example={"Living.TV": 1})):
    for k, v in tags.items():
        gr, name = k.split('.')
        for tak in tako:
            tk = tako[tak]
            if tk['group'] == gr and tk['name'] == name:
                on = tk['btn']['data'] if v else b'\x00'*4
                qmsg.put({'addr': tk['btn']['addr'], 'data': on})
    return tags


def fastapi_run(ini):
    # init fastAPI
    app = FastAPI(title=APPNAME, version=VERSION)
    # app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    #                   allow_methods=["*"], allow_headers=["*"])
    # IMPORTANT include routes in order (first included is first checked)
    app.include_router(route_hub, prefix=f"{ini['API_BASE']}")
    if 'STATIC_DIR' in ini:   # LAST route to include
        app.mount("/", StaticFiles(directory=ini['STATIC_DIR'], html=True), name="static")
    # run main service
    uvicorn.run(app, port=ini['HTTP_PORT'])
    log(f"ERROR: fastapi stopped: http port:{ini['HTTP_PORT']}")


"""-----------------------------------------------------------------------    
    M A I N
------------------------------------------------------------------------"""
if __name__ == '__main__':        # Run from command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', default='el-tako_home.ini', help='config file')
    parser.add_argument('--demo', '-u', default=None, action='store_true', help='demo')
    parser.add_argument('--test', '-t', default=None, help='test read 1:items 2:labels or prodID')
    args = parser.parse_args()

    try:
        with open(args.config, encoding='utf-8') as f:
            ini_rd = json.load(f)
        ini.update(ini_rd)
    except:
        pass
    with open(ini.get('config', args.config.replace('.ini', '.json')), encoding='utf-8') as f:
        tako = json.load(f)

    task_start(tako_run)
    fastapi_run(ini)
