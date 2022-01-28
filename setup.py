# -*- coding: utf-8 -*-
from setuptools import setup


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='rpi-temperature-mqtt',
    version='0.0.7',
    description='Send temperature from DS18B20 sensors to mqtt broker forked fromm https://github.com/ijm51000/rpi-temperature-mqtt.git original author David Uebelacker and Ian Macdonald',
    long_description=readme,
    author='Antti Yliniemi',
    author_email='antti.k.yliniemi@gmail.com',
    url='https://github.com/yliniemi/rpi-temperature-mqtt.git',
    license=license,
    packages=['rpi_temperature_mqtt'],
    install_requires=['paho-mqtt'],
    scripts=['bin/rpi-temperature-mqtt']
)
 
