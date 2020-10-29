#!/usr/bin/python

import paho.mqtt.client as mqtt
import time
import json
import sys

from jsonschema import validate
from jsonschema import exceptions
from uuid import getnode as get_mac
from lib.neo_pixel_string import *
from random import *

# LED strip configuration:
LED_COUNT      = 8      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)



BROKER_ADDRESS = "rpi2"        # broker.mqttdashboard.com
BROKER_PORT = 1883                 # 1883
QOS_STATE_PUBLISH = 1
    # At most once (0)
    # At least once (1)
    # Exactly once (2)
RETAIN_STATE_PUBLISH = True

loopflag = False
animation = 'none'

full_state_schema = {
    "type" : "object",
    "properties" : {
        "state" : {"enum" : ["ON", "OFF"]},
        "effect" : {"enum" : ["rainbow", "rainbowcycle", "theaterchaserainbow", "colorwipe", "theaterchase"]},
        "brightness" : {"type": "number", "minimum": 0, "maximum": 255 },
        "i_hexcolor": {"type": "string", "minimum": 0, "maximum": 10 },
        "color": {
            "type" : "object",
            "properties" : {
                "r" : {"type": "number", "minimum": 0, "maximum": 255 },
                "g" : {"type": "number", "minimum": 0, "maximum": 255 },
                "b" : {"type": "number", "minimum": 0, "maximum": 255 }
            },
            "required": ["r", "g", "b"]
        }
    }
}

neopixelstring = None
topic = "none"

def on_connect(client, userdata, flags, rc):
    m = "Connected flags" + str(flags) + "result code " \
        + str(rc) + "client1_id " + str(client)
    print(m)

def hex2Color(hexcode):
    rgb = tuple(map(ord,hexcode[1:].decode('hex')))
    print("rgb=",rgb)
    return Color(rgb[0],rgb[1],rgb[2])

# This is an interface that is compatible with Home Assistant MQTT JSON Light
def on_message_full_state(client, userdata, message):
    global json_message, loopflag, animation
    json_message = str(message.payload.decode("utf-8"))
    print("message received: ", json_message)

    try:
        data = json.loads(json_message)
        validate(data, full_state_schema)
        if (data.has_key('state')):
            print("got state " + data['state'])
            if (data['state'] == 'ON'):
                neopixelstring.all_on()
            else:
                neopixelstring.all_off()

        if (data.has_key('brightness')):
            neopixelstring.set_brightness(data['brightness'])

        if (data.has_key('color')):
            # For some reason we need to switch r and g. Don't get it
            color = Color(data['color']['g'], data['color']['r'], data['color']['b'])
            neopixelstring.set_color(color)
 
        if (data.has_key('i_hexcolor')):
            i, hex_color = data['i_hexcolor'].split(':',1)
            print("i:",i," ",hex_color)
            neopixelstring.set_i_color(int(i), hex2Color(hex_color))

        if (data.has_key('effect')):
            loopflag = True
            if (data['effect'] == 'rainbow'):
               animation = 'rainbow'
            elif (data['effect'] == 'rainbowcycle'):
               animation = 'rainbowcycle'
            elif (data['effect'] == 'theaterchaserainbow'):
               animation = 'theaterchaserainbow'
            elif (data['effect'] == 'colorwipe'):
               animation = 'colorwipe'
            elif (data['effect'] == 'theaterchase'):
               animation = 'theaterchase'
        else:
            animation = 'none'
            loopflag = False

        publish_state(client)

    except exceptions.ValidationError:
        print "Message failed validation"
    except ValueError:
        print "Invalid json string"

# position of LED used for boiler
boiler_pos = 0

def on_message_boiler(client, userdata, message):
    global boiler_pos
    val = int(message.payload.decode("utf-8"))
    print "on_message_boiler received: ", val
    col = Color(0,255,0) # off g r b
    if (val == 0):
                col = Color(0,0,128) # on g r b
    neopixelstring.set_i_color(boiler_pos, Color(0,0,0))
    boiler_pos = ( boiler_pos + 1 ) % LED_COUNT
    neopixelstring.set_i_color(boiler_pos, col)

def on_message_air(client, userdata, message):
    val = float(message.payload.decode("utf-8"))
    print "on_message_air", message.topic," = ", val
    offset=1
    if (message.topic == 'air/mh-z19b/co2'):
        offset=2
        col = Color(64,0,0) # off g r b
        if (val < 500):
                    col = Color(64,64,0) # on g r b
        elif (val < 1000):
                    col = Color(128 - int(val / 1000 * 128),int(val / 1000 * 128),0) # on g r b
        elif (val < 1500):
                    col = Color(0,int(val / 1500 * 128),int(val / 1500 * 64)) # on g r b
        else:
                    col = Color(0,32,0) # on g r b
    elif (message.topic == 'air/zph02/pm25'):
        offset=4
        col = Color(32,0,0) # off g r b
        if (val > 5):
            col = Color(0,64,0) # off g r b
    else:
        col = Color(0,255,0) # on g r b
                
    neopixelstring.set_i_color( (boiler_pos + offset)     % LED_COUNT, Color(0,0,0))
    neopixelstring.set_i_color( (boiler_pos + offset + 1) % LED_COUNT, col)


def publish_state(client):
    json_state = {
        "brightness": neopixelstring.get_brightness(),
        "state": "OFF" if neopixelstring.is_off() else "ON",
        "color": {
            "r": neopixelstring.get_color()['red'],
            "g": neopixelstring.get_color()['green'],
            "b": neopixelstring.get_color()['blue']
        }
    }

    (status, mid) = client.publish(topic, json.dumps(json_state), \
        QOS_STATE_PUBLISH, RETAIN_STATE_PUBLISH)

    if status != 0:
        print("Could not send state")

# Main program logic follows:
if __name__ == '__main__':
    neopixelstring = NeoPixelString(LED_COUNT, LED_PIN)
    mac = get_mac()

    if (len(sys.argv) != 2):
         print("usage: " + sys.argv[0] + " <topic>\n")
         sys.exit(0)

    topic = sys.argv[1]
    topic_set = topic + "/set"
    print("> using topic '"+topic+"'")
    print("> subscribing to '" + topic_set + "'")

    client1 = mqtt.Client(str(mac) + "-python_client")
    client1.on_connect = on_connect

    # Home Assistant compatible
    client1.message_callback_add(topic_set, on_message_full_state)
    topic_boiler = 'stat/boiler/d';
    client1.message_callback_add(topic_boiler, on_message_boiler)
    topic_air = 'air/#'
    client1.message_callback_add(topic_air, on_message_air)
    #time.sleep(1)

    client1.connect(BROKER_ADDRESS, BROKER_PORT)
    client1.loop_start()
    client1.subscribe(topic_set)
    client1.subscribe(topic_boiler)
    client1.subscribe(topic_air)

    justoutofloop = False
    print ('Press Ctrl-C to quit.')
    while True:
        if loopflag and animation != 'none':
            justoutofloop = True
            if animation == 'rainbow':
                neopixelstring.rainbow()
            elif (animation == 'rainbowcycle'):
               neopixelstring.rainbowCycle()
            elif (animation == 'theaterchaserainbow'):
               neopixelstring.theaterChaseRainbow()
            elif (animation == 'colorwipe'):
               neopixelstring.colorWipe(Color(randint(0,255), randint(0,255), randint(0,255)))
            elif (animation == 'theaterchase'):
               neopixelstring.theaterChase(Color(randint(0,127), randint(0,127), randint(0,127)))
        if not loopflag and justoutofloop:
            justoutofloop = False
            client1.publish(topic, json_message, 0, False)
        time.sleep(.1)

    # This should happen but it doesnt because CTRL-C kills process.
    # Fix later
    print "Disconnecting"
    publish_state(client1)
    client1.disconnect()
    client1.loop_stop()
