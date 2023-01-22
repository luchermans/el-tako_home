# El-tako simple home automation

This is a simple home automation using [Eltako funk Series 14](https://www.eltako.com/en/product-category/professional-smart-home-en/series-14-rs485-bus-rail-mounted-devices-for-the-centralised-wireless-building-installation/)

It simulates a button-press and button-release from wired (FTS14-EM) and
wireless (EnOcean) buttons which are previous learned into the Eltako devices.  
The device status of relais and dimmers are read from the Eltako-bus.

![img/eltako_funk.png](img/eltako_funk.png)

Tested with:

| Device   |                  |
| -------- | ---------------- |
| [FAM14](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FAM14.pdf)    | Antenna module   |
| [FTS14EM](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FTS14EM.pdf)  | Inputs - buttons |
| [FSR14-4x](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FSR14-4x.pdf) | Impulse relais   |
| [FSB14](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FSB14.pdf)    | Roller shutter   |
| [FUD14](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FUD14.pdf)    | Dimmer           |
| [Enocean](https://www.eltako.com/fileadmin/downloads/en/_datasheets/Datasheet_FT55ES-wg.pdf)  | Wireless button  |


## Front-end 
The front-end [www/](www/)index.html shows every (light-)switch ordered into groups.  
Clicking on a switch/button will send a button-press, releasing the button will send a button-release.

http://127.0.0.1:8088  
![img/el-tako_home.png](img/el-tako_home.png)

## Configuration

### Web service

[bin/el-tako_home.ini](bin/el-tako_home.ini)
```
{   "HTTP_PORT": 8088,
    "STATIC_DIR": "../www",
    "API_BASE": "/tako-home/api",
    "COM_PORT": "COM7:57600,n,8,1"  # serial USB port where FAM14 is connected
}
```

Using a REST-API device status is read and button click are simulated.

http://127.0.0.1:8088/docs

![img/el-tako_api.png](img/el-tako_api.png)

Example GET read response:
```
{ "Keuken": {
    "Keuken dim": {"on": 0,"dim": 0},
    "Eettafel": "on": 0}
  },
  "Living": {
    "Zithoek dim": {"on": 0,"dim": 0},
    "Bureau": {"on": 0}
  }
}
```
Example PUT write data:
- button press `{"Living.Bureau":1}`
- button release `{"Living.Bureau":0}`


### el-tako_home.json
In this file the Eltako devices are defined with there corresponding buttons.
The devices have a name and are ordered in groups.

First you need to program your Eltako devices with addresses and learn the actions on buttons.  
Use the [Eltako tool PCT14](https://www.eltako.com/en/software/software-gfvs-pct14.html) to do this.

Every device has an address which is the key in the json below.  
Set the `typ`e of the device, the `group` and `name` you want to appear in the App.  
The `all_off` is not a device it only simulates a button press.  
The `btn` specifies the button address and data to be send on the Eltako func RS485 bus.  
To find the correct btn.addr and .data use PCT14 (see [PCT14_2json.md](PCT14_2json.md)).

`el-tako_home.json`
```
{
    "all_off": {
        "typ": "button", 
        "group": "Central", "name": "Alles uit",
        "btn": {"addr": "00001028", "data": "10000000"}
    },
    "00000004": {
        "typ": "FSB14", 
        "group": "Screens", "name": "Screen Keuken",
        "btn": {"addr": "FEF82C30", "data": "10000000"}
    },
    "00000008": {
        "typ": "FUD14", 
        "group": "Living", "name": "Zithoek dim",
        "btn": {"addr": "00001036", "data": "50000000"}
    },
    "0000000a": {
        "typ": "FUD14",
        "group": "Keuken", "name": "Keuken dim",
        "btn": {"addr": "00001003", "data": "30000000"}
    },
    "0000000c": {
        "typ": "FSR14",
        "group": "Keuken", "name": "Eettafel",
        "btn": {"addr": "00001026", "data": "30000000"}
    }
    "00000013": {
        "typ": "FSR14", 
        "group": "Living", "name": "Bureau",
        "btn": {"addr": "00001006", "data": "30000000"}
    }
}
```

### Install
- Connect the FAM14 USB (virtual serial port)
    - turn the FAM14 wheel BA to Pos. 4
- Copy the directories `bin` and `www`
- set the correct COM port in `bin/el-tako_home.ini`
- create your `bin/el-tako_home.ini`
- Create a virtual env (or use pyinstaller)
    - `pip install -r requirements.txt`
    - `python el-tako_home.py`
- http://127.0.0.1:8088

## LICENSE
El-tako is licensed under the [MIT License](LICENSE.txt).

## TODO
- security
- [connect with Google Home Assitant](https://developers.google.com/assistant/smarthome/overview#how_to_build)

## Refs:

- [Eltako installation manual](https://www.eltako.com/fileadmin/downloads/en/_bedienung/Series_14_RS485_Bus_DIN_Rail_Mounted_DevicesSeries_gb.pdf)
- [Eltako wireless telegrams](https://www.eltako.com/fileadmin/downloads/en/_main_catalogue/Gesamt-Katalog_ChT_gb_highRes.pdf)
- [Eltako PCT14](https://www.eltako.com/en/software-pct14/)
- [FastAPI](https://fastapi.tiangolo.com/)
