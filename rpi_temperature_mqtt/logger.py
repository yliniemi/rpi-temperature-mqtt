import RPi.GPIO as GPIO
import time
import re
import socket
import sys
import traceback

import paho.mqtt.client as mqtt
from threading import Thread

class TemperatureLogger:
    config = None
    mqtt_client = None
    mqtt_connected = False
    worker_sensor = None
    worker_mqtt = None

    def __init__(self, config):
        self.config = config

    @staticmethod
    def median(values):
        if values == []:
            raise NameError("Empty list has no median")
        values.sort()
        if len(values) % 2 == 1:
            return values[len(values) // 2]
        else:
            return (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2

    def verbose(self, message):
        if self.config and "verbose" in self.config and self.config["verbose"] == "true":
            sys.stdout.write("VERBOSE: " + message + "\n")
            sys.stdout.flush()

    def error(self, message):
        sys.stderr.write("ERROR: " + message + "\n")
        sys.stderr.flush()

    def mqtt_connect(self):
        while True:
            if self.mqtt_broker_reachable():
                self.verbose(f"Connecting to {self.config['mqtt_host']}: {self.config['mqtt_port']}")
                self.mqtt_client = mqtt.Client(self.config["mqtt_client_id"])
                if "mqtt_user" in self.config and "mqtt_password" in self.config:
                    self.mqtt_client.username_pw_set(self.config["mqtt_user"], self.config["mqtt_password"])

                self.mqtt_client.on_connect = self.mqtt_on_connect
                self.mqtt_client.on_disconnect = self.mqtt_on_disconnect

                try:
                    self.mqtt_client.connect(self.config["mqtt_host"], int(self.config["mqtt_port"]), 60)
                    self.mqtt_client.loop_forever()
                except:
                    self.error(traceback.format_exc())
                    self.mqtt_client = None
            else:
                self.error(f"{self.config['mqtt_host']}: {self.config['mqtt_port']} not reachable!")
            time.sleep(60)

    def mqtt_on_connect(self, mqtt_client, userdata, flags, rc):
        self.mqtt_connected = True
        self.verbose("...mqtt_connected!")

    def mqtt_on_disconnect(self, mqtt_client, userdata, rc):
        self.mqtt_connected = False
        self.verbose("Disconnected! will reconnect! ...")
        if rc is 0:
            self.mqtt_connect()
        else:
            time.sleep(5)
            while not self.mqtt_broker_reachable():
                time.sleep(10)
            self.mqtt_client.reconnect()

    def mqtt_broker_reachable(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect((self.config["mqtt_host"], int(self.config["mqtt_port"])))
            s.close()
            return True
        except socket.error:
            return False

    def update(self):
        wait_process = 5
        wait_update = 5
        number_of_measurements = 3
        power_pin = -1
        poweroff_cycle = 1000000000
        max_delta = 2.0
        previous_temperatures = {}
        for source in self.config["sources"]:
            # populating this dictionary so there aren't any errors for missing serial entries
            previous_temperatures[source["serial"]] = -1234
        sensor_offline = False
        consecutive_sensor_offlines = 0
        cycle = 0
        delta_too_big = False

        if "wait_process" in self.config:
            wait_process = int(self.config["wait_process"])
        if "wait_update" in self.config:
            wait_update = int(self.config["wait_update"])
        if "number_of_measurements" in self.config:
            number_of_measurements = int(self.config["number_of_measurements"])
        if "power_pin" in self.config:
            power_pin = int(self.config["power_pin"])
            self.verbose(f"power_pin set to: {power_pin}")
        if "poweroff_cycle" in self.config:
            poweroff_cycle = int(self.config["poweroff_cycle"])
            self.verbose(f"will cycle the power every {poweroff_cycle} rounds")
        if "max_delta" in self.config:
            max_delta = float(self.config["max_delta"])
            self.verbose(f"if temperature measurements differ more than {max_delta} C, reboot the sensors")
        if power_pin != -1:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(power_pin, GPIO.OUT)
            GPIO.output(power_pin, GPIO.HIGH)
            time.sleep(10)
        while True:
            cycle += 1
            for source in self.config["sources"]:
                serial = source["serial"]
                topic = source["topic"]
                temperature_list = []
                offset = 0.0
                if "offset" in source:
                    offset = float(source["offset"])

                for _ in range(number_of_measurements):
                    time.sleep(wait_process)
                    try:
                        device = open("/sys/bus/w1/devices/" + serial + "/w1_slave")
                    except IOError:
                        self.verbose(f"Sensor: {serial} not online or wrong id supplied!")
                        sensor_offline = True
                        continue
                    raw = device.read()
                    device.close()
                    match = re.search(r"t=([\d]+)", raw)
                    if match:
                        temperature_raw = match.group(1)
                        temperature_list.append(round(float(temperature_raw) / 1000 + offset, 2))

                if temperature_list != []:
                    temperature = self.median(temperature_list)
                    if (abs(temperature - previous_temperatures[serial]) < max_delta or previous_temperatures[serial] == -1234):
                        self.publish_temperature(topic, temperature)
                        previous_temperatures[serial] = temperature
                    else:
                        self.error(f"{topic} changed too fast")
                        previous_temperatures[serial] = -1234
                        delta_too_big = True
                else:
                    sensor_offline = True

            if sensor_offline == True:
                consecutive_sensor_offlines += 1
            else:
                consecutive_sensor_offlines = 0
            if consecutive_sensor_offlines > 3 or cycle > poweroff_cycle or delta_too_big:
                # I added this clause because my sensors are cheap Chinese knock offs. After a while they go missing or show incorrect temperatures.
                # That is why I"m cutting the power of those bastards.
                # If you want to use this option hook your sensors power_pin to one of the gpio. Power will be cut when sensors go offline.
                # If you want your power to be cut also after a certain time, poweroff_cycle specifies how many times we read the sensors before cutting their power.
                if consecutive_sensor_offlines > 3:
                    self.error("One of the sensors is gone. Rebooting the sensors.")
                if cycle > poweroff_cycle:
                    self.verbose("Poweroff_cycle reached. Maybe the sensors are just fine. Maybe the readings are off. Rebooting just to be on the safe side.")
                if delta_too_big:
                    self.verbose("One of the sensors changed too much from previous measurement. It could be an error. Rebootin the sensors.")

                # If power_pin has been defined, reboot the sensor
                if power_pin != -1:
                    time.sleep(5)
                    GPIO.output(power_pin, GPIO.LOW)
                    time.sleep(15)
                    GPIO.output(power_pin, GPIO.HIGH)
                    time.sleep(15)
                else:
                    self.verbose("Sensor would have been rebooted if power_pin was defined")
                consecutive_sensor_offlines = 0
                cycle = 0
                delta_too_big = False

            sensor_offline = False
            time.sleep(wait_update)
        # This doesn't actually get called since it"s outside an inifinite loop
        GPIO.cleanup()

    def publish_temperature(self, topic, temperature):
        if self.mqtt_connected:
            self.verbose("Publishing: " + topic + " " + str(temperature))
            # False at the end means the message isn't retained. We don't care about temperature when the sensor was last online. We only care about it at this very moment
            self.mqtt_client.publish(topic, str(temperature), 0, False)

    def start(self):
        self.worker_sensor = Thread(target=self.update)
        self.worker_sensor.setDaemon(True)
        self.worker_sensor.start()
        self.worker_mqtt = Thread(target=self.mqtt_connect)
        self.worker_mqtt.setDaemon(True)
        self.worker_mqtt.start()
