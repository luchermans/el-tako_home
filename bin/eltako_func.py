""" enocean esp2 lib    eltako func
    
    TV 1078749171  Jakke123
    https://www.enocean.com/fileadmin/redaktion/support/dolphin-api/esp2_page.html
    
    https://github.com/jnevens/libeltako
    0  1    2     3       4  5  6  7   8  9  10 11     12     13
    A5 5A   0B    05     50 00 00 00   FE FE E2 0E     30     7C
    PRE   | LEN | RORG |     DATA    |    SOURCE   | STATUS | CRC


    # set FUD14 100%
    eltako-send -D /dev/ttyUSB0 -r 0x05 -s30 0xeeeeee00 0x0x02640009
    # set FUD14 to 0% and disable
    eltako-send -D /dev/ttyUSB0 -r 0x05 -s30 0xeeeeee00 0x0x02000008
    # set FSR14 relais on (non blocking)
    eltako-send -D /dev/ttyUSB0 -s 30 0xEEEE2000 -r0x07 0x01000009
    # set FSR14 relais off (non blocking)
    eltako-send -D /dev/ttyUSB0 -s 30 0xEEEE2000 -r0x07 0x01000008
    # FSB blinds up 3s
    eltako-send -D /dev/ttyUSB0 -s 30 0xEEEE3000 -r0x07 0xff030108
    # FSB blinds down 3s
    eltako-send -D /dev/ttyUSB0 -s 30 0xEEEE3000 -r0x07 0xff030208
    # FSB blinds stop
    eltako-send -D /dev/ttyUSB0 -s 30 0xEEEE3000 -r0x07 0xff000008
    
    FTS14EM E1=0x70 Up Right E2=0x50 Bottom Right E3=0x30 Up Left E4=0x10 Bottom Left
            E5=0x70 E6=0x50 E7=0x30 E8=0x10 E9=0x70 E10=0x50 
    
"""
from __future__ import print_function
from builtins import bytes
import sys
import time
import datetime
import serial

""" LOGGING """
SHOWHEX = True
buff = b''


def str_2hex(data):
    if type(data) == bytes:
        return '.'.join([('%02X' % o) for o in data])
    return '.'.join([('%02X' % ord(o)) for o in data])


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def log(head, data=''):
    fmat = '%s ' + head + '%s'
    print(fmat % (now(), str_2hex(data) if SHOWHEX else repr(data)))


""" SERIAL """
def ser_open(comx='COM3:115200,N,8,1', tout=0.2):
    baud = 115200
    party = 'N'
    bits = 8
    stop = 1
    com = comx.split(':')
    if len(com)>1:
        pbs = com[1].split(',')
        baud = int(pbs[0])
        if len(pbs)>1: party = pbs[1]
        if len(pbs)>2: bits = int(pbs[2])
        if len(pbs)>3: stop = int(pbs[3])
    print('open %s:%s,%s,%s,%s' % (com[0], baud, party, bits, stop))
    ser = serial.Serial(port=com[0], baudrate=baud, bytesize=bits, parity=party, stopbits=stop, timeout=tout, xonxoff=0, rtscts=0)
    return ser

def ser_write(ser, data):
    log('-> ', data)
    ser.write(data)

def ser_read(ser, buff, LOG=False):
    data = ser.read(128)
    if type(data) == str:   #python 2.6
        data = bytes(data)
    if len(data) > 0:
        buff += data
        if LOG:
            log('<- ', data)
    
    return buff


""" ENOCEAN ESP2 """
# CONSTANTS
SYNC = b'\xA5\x5A'
FAM14 = b'\xff\xe4\x69\x00'

# HSEQ_TYPE
HSEQ_RRT = 0 # .0B Receive radio telegram: AIR->DOLPHIN->HOST
HSEQ_TRT = 3 # .6B Transmit radio telegram: HOST->DOLPHIN->AIR
HSEQ_RCT = 4 # .8B Receive command telegram DOLPHIN->HOST
HSEQ_TCT = 5 # .AB Transmit command telegram: HOST->DOLPHIN

# ORG TYPE  experimental f0 f1 f2 f8 fc ff
ORG_RPS = 0x5   # fc poll  fe force poll
ORG_1BS = 0x6   # f0 discovery
ORG_4BS = 0x7
ORG_HRC = 0x8
ORG_SYS = 0x9

def packet(data=b'\x00\x00\x00\x00', addr=b'\x00\x00\x00\x00', status=0x30, org=ORG_4BS, hseq=HSEQ_TCT):
    """ packet A5.5A.HLEN.ORG.DATA.CSUM
        where HLEN = 3bit (type) + 5bit (length)
    """
    data += addr + bytes([status])
    hlen = (len(data) + 2) | (hseq << 5)
    data = bytes([hlen, org]) + data
    pack = SYNC + data + bytes([sum(data) % 256])
    return pack

def packet_fnd():
    global buff
    p = buff.find(SYNC)
    if p >= 0:
        buff = buff[p:]
    if len(buff) < 14:
        return None
    pack = buff[:14]
    buff = buff[14:]
    cs = sum(pack[2:13]) % 256
    if cs != pack[13]:
        log('ERROR csum: ', pack)
    elif pack[3:12] == b'\xfc' + b'\x00' * 8:
        print(f"%02x {(pack[12]%8)*'.'}    \r" % pack[12], end="", flush=True)
    else:
        log('<- ', pack)
    return pack


def main():
    global buff
    ser = ser_open('COM3:57600')
    cnt = 1000
    adr = 0
    s = packet(org=0xff, status=0x00)
    ser_write(ser, s)
    while 1:
        buff = ser_read(ser, buff)
        d = packet_fnd()
        cnt += 1
        if cnt == 10:
            ser_write(ser, button())
        if cnt == 11:
            ser_write(ser, button(on=False))
        if cnt == 1010:
            ser_write(ser, relais())
        if cnt == 1810:
            ser_write(ser, relais(on=False))
        if cnt % 115 == 0:
            ser_write(ser, poll())
        if cnt % 195 == 0:
            ser_write(ser, poll(b'\x0a'))

def to_addr(a):
    if not isinstance(a, (bytes, bytearray)):
        a = a.to_bytes(4, 'big')
    return b'\x00' * (4-len(a)) + a

def button(addr=b'\x00\x00\x10\x23', on=True):
    if on:  return packet(data=b'\x30\x00\x00\x00', addr=to_addr(addr), org=5, hseq=0)
    else:   return packet(data=b'\x00\x00\x00\x00', addr=to_addr(addr), org=5, status=0x20, hseq=0) #, hseq=HSEQ_TRT)

def relais(addr=b'\x0D', on=True):
    if on:  return packet(data=b'\x01\x00\x00\x09', addr=to_addr(0), org=7, status=addr[0])
    else:   return packet(data=b'\x01\x00\x00\x08', addr=to_addr(0), org=7, status=addr[0])

def status(addr=b'\x0D'):
    return packet(data=b'\x00\x00\x00\x00', addr=to_addr(0), org=0xfe, status=addr[0])
    return packet

def poll(addr=b'\x0d'):
    return packet(data=b'\x00\x00\x00\x00', addr=to_addr(0), org=0xfc, status=addr[0])
    return packet

def discover(addr):
    return packet(data=b'\x00\x00\x00\x00', addr=to_addr(0), org=0xf0)
    return packet

"""-----------------------------------------------------------------------
    M A I N       P R O G R A M
------------------------------------------------------------------------"""
if __name__ == "__main__":
    main()
    sys.exit()

    """   A5.5A.HLEN.ORG.D3210.ID3210 STAT.CSUM
             1  2  3  4  5  9  7  8  9  A  CS
    a5 5a ab ff 00 00 00 00 00 00 00 00 00 aa  -> tx   ID detection on
    a5 5a 8b f0 ff 01 7f 00 07 ff 15 00 00 15  <- rx
    a5 5a ab ff 00 00 00 00 00 00 00 00 ff a9  -> tx   ID detection off
    a5 5a ab f2 00 00 00 00 00 00 00 00 0b a8  -> tx
    a5 5a 8b f2 00 00 00 00 00 00 00 00 0b 88  <- rx
    a5 5a ab f4 00 00 10 27 02 15 0f 00 0d 09  -> tx
    a5 5a 8b f4 00 00 10 27 02 15 0f 00 0d e9  <- rx

    a5 5a ab f0 00 00 00 00 00 00 00 00 01 9c  -> Adr 001   Read devices
    a5 5a 8b f0 01 02 87 08 04 06 52 00 00 69
    a5 5a ab f0 00 00 00 00 00 00 00 00 02 9d  -> Adr 002
    a5 5a 8b f8 00 00 00 00 00 00 00 00 00 83
    a5 5a ab f0 00 00 00 00 00 00 00 00 03 9e  -> Adr 003
    a5 5a 8b f0 03 02 87 08 04 06 52 00 00 6b
    a5 5a ab f0 00 00 00 00 00 00 00 00 04 9f  -> Adr 004
    a5 5a 8b f8 00 00 00 00 00 00 00 00 00 83
    a5 5a ab f0 00 00 00 00 00 00 00 00 04 9f  -> tx    Read devices
    a5 5a 8b f8 00 00 00 00 00 00 00 00 00 83  <- rx    04, 05 is seq nr ???
    a5 5a ab f0 00 00 00 00 00 00 00 00 05 a0  -> tx
    a5 5a 8b f0 05 02 87 08 04 06 52 00 00 6d  <- rx
    a5 5a ab f0 00 00 00 00 00 00 00 00 07 a2
    a5 5a 8b f0 07 01 7f 08 04 04 3a 00 00 4c 
    a5 5a ab f0 00 00 00 00 00 00 00 00 0f aa  -> Adr 015
    a5 5a 8b f0 0f 04 7f 08 04 01 51 00 00 6b    
    a5 5a ab f1 00 00 00 00 00 00 00 01 ff 9c  -> tx
    a5 5a 8b f1 ff e4 69 00 00 00 00 00 01 c9  <- rx
     
    a5 5a 0b 05 70 00 00 00 00 00 10 01 30 c1  <- rx  70 On   ORG 05 AIR->DOLPHIN->HOST
    a5 5a 0b 05 50 00 00 00 00 00 10 02 30 a2  <- rx  50 Off
    a5 5a 0b 05 00 00 00 00 00 00 10 47 20 87  <- rx
    
    0b 0000 1011  000 =0 = RRT AIR->DOLPHIN->HOST len = ob = 01011 = 11
    ab 1010 1011  101 =5 = TCT HOST->DOLPHIN
    8b 1000 1011  100 =4 = RCT DOLPHIN->HOST
    len = len(data)+1
    """
    s = packet(org=0xfc)
    log('tx ', s)
    
    buff = b'\xa5\x5a\x8b\xf0\xff\x01\x7f\x00\x07\xff\x15\x00\x00\x15'
    buff += b'\xA5\x5A\xAB\xFC\x00\x00\x00\x00\x00\x00\x00\x00\x0A\xB1'
    buff += b'\xa5\x5a\x8b\xf0\x17\x04\x7f\x08\x04\x01\x51\x00\x00\x73'
    buff += b'\xA5\x5A\xAB\xFC\x00\x00\x00\x00\x00\x00\x00\x00\x0A\xB1'
    buff += bytes([0xa5, 0x5a, 0x8b, 0xf0, 0x17, 0x04, 0x7f, 0x08, 0x04, 0x01, 0x51, 0x00, 0x00, 0x73])
    buff += b'\xA5\x5A\xAB\xFC\x00\x00\x00\x00\x00\x00\x00\x00\x0A\xB1'
    buff += bytes([0x55, 0x5a, 0x8b, 0xf0, 0x17, 0x04, 0x7f, 0x08, 0x04, 0x01, 0x51, 0x00, 0x00, 0x73]) + s
    buff += bytes([0x55, 0x5a, 0x8b, 0xf0, 0x17, 0x04, 0x7f])
    buff += b'\xa5\x5a\x8b\xf0\xff\x01\x7f\x00\x07\xff\x15\x00\x00\x15'
    while 1:
        d = packet_fnd()
        if d is None:
            break