DS18B20 Temperature to mqtt for Raspberry Pi
=============================

Reads the the temperature of DS18B20 sensors and sends it to a mqtt broker.


Installation:
-------------------

Clone the repo

For python2, from the bash prompt, enter:

$ sudo python setup.py install


Configuration:
-------------------

Needs a json configuration file as follows (don't forget to change ip and credentials ;-)):


.. code:: json

    {
        "mqtt_client_id": "environmental_sensors",
        "mqtt_host": "192.168.0.210",
        "mqtt_port": "1883",
        "sources": [
            {
              "serial": "10-0008031e4d9e",
              "topic": "tele/ServerRoom/rack0_front_bottom",
              "device": "rack0_lower_front"
            },
            {
             "serial": "10-0008031e804b",
             "topic": "tele/ServerRoom/rack0_front_top",
             "device": "rack0_upper_front"            },
            {
              "serial": "10-0008031eaac7",
             "topic": "tele/ServerRoom/rack0_front_rear",
              "device": "rack0_upper_rear"            }
          ]
    }


Optional json variables:
-------------------

Wait before query all sensors again (defaults to 10 seconds)
    
    "wait_update": "60",
    
Wait between sensor reads (defaults to 5 seconds)
    
    "wait_process": "3",
    
In case your mqtt has user and passwd
    
    "mqtt_user": "username",
    
    "mqtt_password": "password",

You may enable verbose mode to catch issues, also enable for systemd 

    "verbose": "true",

If your sensor is misbehaving you can power it from one of the gpio pins so it can be rebooted if it locks up

    "power_pin": "17",

My sensor is really naughty and gives false results after a few hours. I reboot it every once in a while with this setting.
This means that it will be rebooted even if no probleams arise after reading the sensors a 1000 times.

    "poweroff_cycle": "1000",


Start:
-------------------

    rpi-temperature-mqtt config.json
