#!/usr/bin/env python

import argparse
import datetime
import os
import time
from time import sleep
import socket
import json

import jwt
import paho.mqtt.client as mqtt
from sense_hat import SenseHat

sense = SenseHat()
sense.clear()

# [START iot_mqtt_jwt]
def create_jwt(project_id, private_key_file, algorithm):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
        Args:
         project_id: The cloud project ID this device belongs to
         private_key_file: A path to a file containing either an RSA256 or
                 ES256 private key.
         algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
        Returns:
            An MQTT generated from the given project_id and private key, which
            expires in 20 minutes. After 20 minutes, your client will be
            disconnected, and a new JWT will have to be generated.
        Raises:
            ValueError: If the private_key_file does not contain a known key.
        """

    token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    print('Creating JWT using {} from private key file {}'.format(
            algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm)
# [END iot_mqtt_jwt]


# [START iot_mqtt_config]
def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return '{}: {}'.format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print('on_connect', mqtt.connack_string(rc))

def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print('on_disconnect', error_str(rc))


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    print('on_publish')
    sense.set_pixel(1, 1, (0,255,0))
    sleep(0.5)
    sense.set_pixel(1, 1, (0,0,0))
    sleep(0.5)


def on_message(unused_client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = str(message.payload)
    print('Received message \'{}\' on topic \'{}\' with Qos {}'.format(
            payload, message.topic, str(message.qos)))
    config =  json.loads(payload)
    sense.clear(config['red'], config['green'], config['blue'])

def get_client(
        project_id, cloud_region, registry_id, device_id, private_key_file,
        algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client = mqtt.Client(
            client_id=('projects/{}/locations/{}/registries/{}/devices/{}'
                       .format(
                               project_id,
                               cloud_region,
                               registry_id,
                               device_id)))

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(
            username='unused',
            password=create_jwt(
                    project_id, private_key_file, algorithm))

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = '/devices/{}/config'.format(device_id)

    # Subscribe to the config topic.
    client.subscribe(mqtt_config_topic, qos=1)

    # Start the network loop.
    client.loop_start()

    return client
# [END iot_mqtt_config]


def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=(
            'Example Google Cloud IoT Core MQTT device connection code.'))
    parser.add_argument(
            '--project_id',
            default=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            help='GCP cloud project name')
    parser.add_argument(
            '--registry_id', required=True, help='Cloud IoT Core registry id')
    parser.add_argument(
            '--device_id', required=True, help='Cloud IoT Core device id')
    parser.add_argument(
            '--private_key_file',
            required=True, help='Path to private key file.')
    parser.add_argument(
            '--algorithm',
            choices=('RS256', 'ES256'),
            required=True,
            help='Which encryption algorithm to use to generate the JWT.')
    parser.add_argument(
            '--cloud_region', default='us-central1', help='GCP cloud region')
    parser.add_argument(
            '--ca_certs',
            default='roots.pem',
            help=('CA root from https://pki.google.com/roots.pem'))
    parser.add_argument(
            '--num_messages',
            type=int,
            default=100,
            help='Number of messages to publish.')
    parser.add_argument(
            '--message_type',
            choices=('event', 'state'),
            default='event',
            help=('Indicates whether the message to be published is a '
                  'telemetry event or a device state message.'))
    parser.add_argument(
            '--mqtt_bridge_hostname',
            default='mqtt.googleapis.com',
            help='MQTT bridge hostname.')
    parser.add_argument(
            '--mqtt_bridge_port',
            choices=(8883, 443),
            default=8883,
            type=int,
            help='MQTT bridge port.')

    return parser.parse_args()


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


# [START iot_mqtt_run]
def main():
    args = parse_command_line_args()

    # sensor setup
    #sense = SenseHat()
    sense.clear()
    #with open('./deviceinfo.json') as json_data:
    #    device_config = json.load(json_data)
    ip = get_ip_address()
    hostname = socket.gethostname()

    # Publish to the events or state topic based on the flag.
    sub_topic = 'events' if args.message_type == 'event' else 'state'

    mqtt_topic = '/devices/{}/{}'.format(args.device_id, sub_topic)
    client = get_client(
        args.project_id, args.cloud_region, args.registry_id, args.device_id,
        args.private_key_file, args.algorithm, args.ca_certs,
        args.mqtt_bridge_hostname, args.mqtt_bridge_port
        )

    # Publish num_messages messages to the MQTT bridge once per second.
    #for i in range(1, args.num_messages + 1):
    i = 0
    while True:
        data = {}
        d = datetime.datetime.utcnow()

        o = sense.get_orientation()
        x = o["pitch"]
        y = o["roll"]
        z = o["yaw"]

        button_pressed = False
        for event in sense.stick.get_events():
            if (event.action =="pressed") or (event.action=="held"):
                button_pressed = True
            else:
                button_pressed = False

        pressure = sense.get_pressure()
        temp_c = sense.get_temperature()
        temperature = (temp_c * 1.8) + 32
        humidity = sense.get_humidity()

        data['device_id'] = '1'
        data['city'] = 'AMSTERDAM'
        data['country'] = 'NL'
        data['region'] = 'EUROPE'
        data['lat'] = '0'
        data['long'] = '0'
        data["timestamp"] = d.isoformat("T") + "Z"
        data['button_pressed'] = button_pressed
        data['orientation'] = {'x': x, 'y': y, 'z': z}
        data['temperature'] = str(round(temperature, 2))
        data['humidity'] = str(round(humidity, 2))
        data['pressure'] = str(round(pressure, 2))
        data['light_level'] = 1

        data['ip_address'] = ip
        data['hostname'] = hostname

        payload = json.dumps(data).encode('utf-8')
        print('Publishing message {}/{}: \'{}\''.format(
                i, args.num_messages, payload))

        # Publish "payload" to the MQTT topic. qos=1 means at least once
        # delivery. Cloud IoT Core also supports qos=0 for at most once
        # delivery.
        client.publish(mqtt_topic, payload, qos=1)

        # Send events every second. State should not be updated as often
        time.sleep(60 if args.message_type == 'event' else 300)
        i += 1

    # End the network loop and finish.
    client.loop_stop()
    print('Finished.')
# [END iot_mqtt_run]

if __name__ == '__main__':
    main()