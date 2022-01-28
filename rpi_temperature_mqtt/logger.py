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
    temperatures = {}

    def __init__(self, config):
        self.config = config

    def median(values):
        if values == []:
            raise NameError('Empty list has no median')
        values.sort()
        if len(values) % 2 == 1:
            return values[len(values) // 2]
        else:
            return (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2

    def verbose(self, message):
        if self.config and 'verbose' in self.config and self.config['verbose'] == 'true':
            sys.stdout.write('VERBOSE: ' + message + '\n')
            sys.stdout.flush()

    def error(self, message):
        sys.stderr.write('ERROR: ' + message + '\n')
        sys.stderr.flush()

    def mqtt_connect(self):
        while True:
            if self.mqtt_broker_reachable():
                self.verbose('Connecting to ' + self.config['mqtt_host'] + ':' + self.config['mqtt_port'])
                self.mqtt_client = mqtt.Client(self.config['mqtt_client_id'])
                if 'mqtt_user' in self.config and 'mqtt_password' in self.config:
                    self.mqtt_client.username_pw_set(self.config['mqtt_user'], self.config['mqtt_password'])

                self.mqtt_client.on_connect = self.mqtt_on_connect
                self.mqtt_client.on_disconnect = self.mqtt_on_disconnect

                try:
                    self.mqtt_client.connect(self.config['mqtt_host'], int(self.config['mqtt_port']), 60)
                    self.mqtt_client.loop_forever()
                except:
                    self.error(traceback.format_exc())
                    self.mqtt_client = None
            else:
                self.error(self.config['mqtt_host'] + ':' + self.config['mqtt_port'] + ' not reachable!')
            time.sleep(60)

    def mqtt_on_connect(self, mqtt_client, userdata, flags, rc):
        self.mqtt_connected = True
        self.verbose('...mqtt_connected!')

    def mqtt_on_disconnect(self, mqtt_client, userdata, rc):
        self.mqtt_connected = False
        self.verbose('Disconnected! will reconnect! ...')
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
            s.connect((self.config['mqtt_host'], int(self.config['mqtt_port'])))
            s.close()
            return True
        except socket.error:
            return False

    def update(self):
        wait_process = 5
        wait_update = 300
        power_pin = -1
        poweroff_cycle = 1000000000
        sensor_offline = False
        consecutive_sensor_offlines = 0
        cycle = 0
        if 'wait_process' in self.config:
            wait_process = int(self.config['wait_process'])
        if 'wait_update' in self.config:
            wait_update = int(self.config['wait_update'])
        if 'power_pin' in self.config:
            power_pin = int(self.config['power_pin'])
            self.verbose('power_pin set to: ' + str(power_pin))
        if 'poweroff_cycle' in self.config:
            poweroff_cycle = int(self.config['poweroff_cycle'])
            self.verbose('will cycle the power every ' + str(poweroff_cycle) + ' rounds')
        if power_pin != -1:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(power_pin, GPIO.OUT)
            GPIO.output(power_pin, GPIO.HIGH)
            time.sleep(10)
        while True:
            cycle += 1
            for source in self.config['sources']:
                time.sleep(wait_process)
                serial = source['serial']
                topic = source['topic']
                try:
                    # if sensor is disappearing we still want data from others
                    device = open('/sys/bus/w1/devices/' + serial + '/w1_slave')
                except IOError:
                    self.verbose("Sensor: {} not online or wrong id supplied!".format(serial))
                    sensor_offline = True
                    continue
                raw = device.read()
                device.close()
                match = re.search(r't=([\d]+)', raw)
                if match:
                    temperature_raw = match.group(1)
                    temperature = round(float(temperature_raw)/1000, 2)

                    if 'offset' in source:
                        temperature += float(source['offset'])

                    self.temperatures[serial] = temperature
                    self.publish_temperature(topic, temperature)

            if sensor_offline == True:
                consecutive_sensor_offlines += 1
            else:
                consecutive_sensor_offlines = 0
            if (consecutive_sensor_offlines > 3 or cycle > poweroff_cycle) and power_pin != -1:
                # I added this clause because my sensors are cheap Chinese knock offs. After a while they go missing or show incorrect temperatures.
                # That is why I'm cutting the power of those bastards.
                # If you want to use this option hook your sensors power_pin to one of the gpio. Power will be cut when sensors go offline.
                # If you want your power to be cut also after a certain time, poweroff_cycle specifies how many times we read the sensors before cutting their power.
                if consecutive_sensor_offlines > 3:
                    self.error("One of the sensors is gone. Rebooting the sensors.".format(serial))
                if cycle > poweroff_cycle:
                    self.verbose("poweroff_cycle reached. Maybe the sensors are just fine. Maybe the readings are off. Rebooting just to be on the safe side.".format(serial))
                time.sleep(5)
                GPIO.output(power_pin, GPIO.LOW)
                time.sleep(15)
                GPIO.output(power_pin, GPIO.HIGH)
                time.sleep(15)
                consecutive_sensor_offlines = 0
                cycle = 0
            sensor_offline = False
            time.sleep(wait_update)
        # This doesn't actually get called since it's outside an inifinite loop
        GPIO.cleanup()

    def publish_temperature(self, topic, temperature):
        if self.mqtt_connected:
            self.verbose('Publishing: ' + topic + " " + str(temperature))
            # False at the end means the message isn't retained. We don't care about temperature when the sensor was last online. We only care about it at this very moment
            self.mqtt_client.publish(topic, str(temperature), 0, False)

    def start(self):
        self.worker_sensor = Thread(target=self.update)
        self.worker_sensor.setDaemon(True)
        self.worker_sensor.start()
        self.worker_mqtt = Thread(target=self.mqtt_connect)
        self.worker_mqtt.setDaemon(True)
        self.worker_mqtt.start()
