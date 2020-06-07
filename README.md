DS18B20 Temperature to mqtt for Raspberry Pi
=============================

Reads the the temperature of DS18B20 sensors and sends it to a mqtt broker.


Installation:
-------------------

Clone the repo

For python2, from the bash prompt, enter:
```
$ sudo apt-get install -y python-setuptools
$ sudo python setup.py install
```
Configuration:
-------------------

You can list available 1wire devices like so
DS18B20 devices typically start **28-**
> $ ls /sys/bus/w1/devices
> 28-0004330feaff  w1_bus_master1

you can get a raw temperature reading 
$ cat /sys/bus/w1/devices/28-0004330feaff/w1_slave
```
59 01 55 00 7f ff 0c 10 bc : crc=bc YES
59 01 55 00 7f ff 0c 10 bc t=21562 # t=temperature / 1000 = 21.562
```
Need to define json configuration file as follows, changing values to suit your 
needs and device ID's


.. code:: json

    {
        "mqtt_client_id": "my_client_name",
        "mqtt_host": "localhost",
        "mqtt_port": "1883",
        "sources": [
            {
              "serial": "28-0008031e4d9e",
              "topic": "tele/ServerRoom/rack0_front_bottom",
              "device": "rack0_lower_front"
            },
            {
             "serial": "28-0008031e804b",
             "topic": "tele/ServerRoom/rack0_front_top",
             "device": "rack0_upper_front"            },
            {
              "serial": "28-0008031eaac7",
             "topic": "tele/ServerRoom/rack0_front_rear",
              "device": "rack0_upper_rear"            }
          ]
    }


Optional json variables:
-------------------

Wait before query all sensors again (defaults to 300)
    
    "wait_update": 60.0,
    
Wait between sensor reads (defaults to 5)
    
    "wait_process": 3.0,
    
In case your mqtt has user and passwd
    
    "mqtt_user": "username",
    
    "mqtt_password": "password",

You may enable verbose mode to catch issues, also enable for systemd 

    "verbose": "true",


Start:
-------------------
CLI:
   > rpi-temperature-mqtt config.json

Systemd
   ```
   sudo mkdir  /etc/rpi-temperature-mqtt/
   sudo cp my_config.json  /etc/rpi-temperature-mqtt/rpi_temp_config.json
   sudo cp systemd/rpi_sensors_mqtt.service  /lib/systemd/system/rpi-sensors-mqtt.service
   sudo systemctl daemon-reload 
   sudo systemctl enable rpi-sensors-mqtt.service # to enable start at system boot
   sudo systemctl start rpi-sensore-mqtt.service # start now 
   ```
