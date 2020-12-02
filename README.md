# Raspberry PI NeoPixel to mqtt bridge

Very simple mqtt client app in Python that allows control of NeoPixel ring
using mqtt.

based on https://github.com/BioBoost/saito_mqtt_bed_neopixels

Makes use of Jeremy Garffs neopixel lib for the Rpi. More info at:

* https://learn.adafruit.com/neopixels-on-raspberry-pi?view=all
* https://github.com/jgarff/rpi_ws281x

## Installing rpi_ws281x

```shell
sudo apt-get update
sudo apt-get install build-essential python-dev git scons swig
cd ; git clone https://github.com/jgarff/rpi_ws281x.git
cd rpi_ws281x
scons
cd python
sudo python setup.py install
```

## Other requirements

You also need jsonschema and paho mqtt libs.

```shell
sudo pip install jsonschema
sudo pip install paho-mqtt
```

## Hardware

Currently library defaults to GPIO10 

## OPENHAB2

see openhab2 directory for basic examples


## Autostart on Raspberry Pi

using systemd:

```shell
cd /opt/neopixel_mqtt
chmod +x app.py

sudo su
cp neopixel_mqtt.service /etc/systemd/system
systemctl enable neopixel_mqtt.service
systemctl start neopixel_mqtt.service
```

## testing

Simulate tasmota power events from switch:

```shell
mosquitto_pub -h rpi2 -t 'stat/ir/POWER' -m ON
mosquitto_pub -h rpi2 -t 'stat/ir/POWER' -m OFF
```
