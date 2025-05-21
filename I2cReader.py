import json
import uuid
import time
import random
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

TEST_INPUT = True

if not TEST_INPUT:
    from dfrobot_airqualitysensor import *
    from DFRobot_SHT3X import *

    I2C_1 = 0x01  # I2C_1 Use i2c1 interface (or i2c0 with configuring Raspberry Pi file) to drive sensor
    I2C_ADDRESS = 0x19  # I2C Device address, which can be changed by changing A1 and A0, the default address is 0x54
    airqualitysensor = DFRobot_AirQualitySensor(I2C_1, I2C_ADDRESS)

    SHT3X = DFRobot_SHT3x(iic_addr=0x45, bus=1)

MQTT_BROKER = '127.0.0.1'
MQTT_PORT = 1883
MQTT_TOPIC = 'pi/sensors'

def create_opcua_json_message(payload: str) -> str:
    message = {
        "MessageId": uuid.uuid4().hex,
        "MessageType": "ua-data",
        "PublisherId": "publisher-1",
        "Messages": [
            {
                "DataSetWriterId": "writer-1",
                "Timestamp": datetime.now(timezone.utc).isoformat(),
                "Payload": {
                    "Message": payload
                }
            }
        ]
    }
    return json.dumps(message, indent=2)

def create_json_message(payload: str) -> str:
    message = {
        "DataSetWriterId": "writer-1",
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "Message": payload
    }
    return json.dumps(message, indent=2)

def send_mqtt_message(client, client2, topic, topic2, message):
    client.publish(topic, message)
    if client2:
        client2.publish(topic2, message)
    print(f"Sent MQTT message to topic '{topic}'")

def connect_mqtt(broker: str, username: str, password: str) -> Client | None:
    try:
        host, port_str = broker.split(":")
        port = int(port_str)
    except ValueError:
        return None

    client = mqtt.Client()

    if username or password:
        client.username_pw_set(username, password)

    client.connect(host, port)

    return client

def read_settings(settings_file: str):
    try:
        with open(settings_file) as f:
            settings = json.load(f)
            return settings.get("broker", None), settings.get("username", None), settings.get("password", None), settings.get("topic", None)
    except Exception as e:
        print(e)
        return None, None, None, None

def main():
    #SETUP
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

    broker, username, password, topic = read_settings("./settings.json")
    lbroker, lusername, lpassword, ltopic = broker, username, password, topic
    if broker:
        forward_client = connect_mqtt(broker, username, password)
    else:
        forward_client = None

    if not TEST_INPUT:
        time.sleep(1)
        version = airqualitysensor.gain_version()
        print(f"version is : {str(version)}")
        time.sleep(1)

        while SHT3X.begin(RST=4) != 0:
            print("The initialization of the chip is failed, please confirm whether the chip connection is correct")
            time.sleep(1)

        print(f"The chip serial number = {SHT3X.read_serial_number()} ")

        if not SHT3X.soft_reset():
            print("Failed to reset the chip")

    message = {}

    #MAIN
    while True:
        if TEST_INPUT:
            message["PM1"] = random.randrange(11)
            message["PM2"] = random.randrange(250)
            message["PM10"] = random.randrange(11)
            message["T"] = random.uniform(-10, 30)
            message["H"] = random.uniform(0, 100)
            time.sleep(1)
        else:
            message["PM1"] = airqualitysensor.gain_particle_concentration_ugm3(airqualitysensor.PARTICLE_PM1_0_STANDARD)
            message["PM2"] = airqualitysensor.gain_particle_concentration_ugm3(airqualitysensor.PARTICLE_PM2_5_STANDARD)
            message["PM10"] = airqualitysensor.gain_particle_concentration_ugm3(airqualitysensor.PARTICLE_PM10_STANDARD)

            time.sleep(0.5)

            message["T"] = SHT3X.get_temperature_C()
            message["H"] = SHT3X.get_humidity_RH()

            time.sleep(0.5)

        payload_str = json.dumps(message, indent=2)
        print(f"Received data: {payload_str}")
        opc_ua_message = create_opcua_json_message(payload_str.rstrip('x\00'))
        print(opc_ua_message)

        broker, username, password, topic = read_settings("./settings.json")
        if broker != lbroker or username != lusername or password != lpassword or topic != ltopic:
            if broker:
                forward_client = connect_mqtt(broker, username, password)
            else:
                forward_client = None
            lbroker, lusername, lpassword, ltopic = broker, username, password, topic

        send_mqtt_message(mqtt_client, forward_client, MQTT_TOPIC, topic, opc_ua_message)

if __name__ == "__main__":
    main()
