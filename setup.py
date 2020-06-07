# -*- coding: utf-8 -*-
from setuptools import setup


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='rpi-temperature-mqtt',
    version='0.0.6',
    description='Send temperature from DS18B20 sensors to mqtt broker forked fromm https://github.com/goodfield/rpi-temperature-mqtt.git original author David Uebelacker',
    long_description=readme,
    author='Ian Macdonald',
    author_email='ianmac51@gmail.com',
    url='https://github.com/ijm51000/rpi-temperature-mqtt.git',
    license=license,
    packages=['rpi_temperature_mqtt'],
    install_requires=['paho-mqtt'],
    scripts=['bin/rpi-temperature-mqtt']
)
 
