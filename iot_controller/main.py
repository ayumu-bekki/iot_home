import signal
import sys
import logging
import json
import time
from paho.mqtt import client as mqtt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# MQTT Broker
BROKER_ADDRESS = "mosquitto"
BROKER_PORT = 1883
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

# MQTT Device 
IRRIGATION_SYSTEM_ID = "0001"
INFORMATION_PANEL_ID = "0001"
IOT_CONTROLLER_ID = "0001"

# InfluxDB
INFLUXDB_URL = "http://influxdb:8086"
TOKEN = "mytoken123456789"
ORG = "iothomeorg"
BUCKET = "iothomebucket"

info_panel_update_time = 0
last_status_update_time = 0

def seconds_until_midnight():
    # 現在の時刻から、その日の終わり（真夜中、23:59:59）までの秒数を計算して返します。
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) # 次の日の0時0分0秒（真夜中）を計算
    time_remaining = midnight - now
    seconds = time_remaining.total_seconds()
    return int(seconds)

def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"Connected with result code {rc}")
    
    client.subscribe('irrigation_system/' + IRRIGATION_SYSTEM_ID + '/status');
    client.subscribe('irrigation_system/' + IRRIGATION_SYSTEM_ID + '/telemetry/voltage');
    client.subscribe('irrigation_system/' + IRRIGATION_SYSTEM_ID + '/events/watering');

def on_disconnect(client, userdata, rc):
    logging.info(f"Disconnectet with result code コード: {rc}")

    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info(f"Try Connect {reconnect_delay} sec ago")
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Re Connected")
            return
        except Exception as err:
            logging.error(f"Failed re connected {err}")

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1

    logging.error("Failed Re Connected")

def on_message(client, userdata, msg):
    logging.info(f"Topic: {msg.topic}")
    logging.info(f"Payload: {msg.payload.decode()}")

    message_functions = {
        "irrigation_system/" + IRRIGATION_SYSTEM_ID + "/status": recv_status,
        "irrigation_system/" + IRRIGATION_SYSTEM_ID + "/telemetry/voltage": recv_voltage,
        "irrigation_system/" + IRRIGATION_SYSTEM_ID + "/events/watering": recv_event_watering,
    }
    func = message_functions.get(msg.topic)
    if func:
        func(client, userdata, msg)
    else:
        logging.warn("Not Exists function topic")


def recv_voltage(client, userdata, msg):
    json_data = json.loads(msg.payload.decode()) 
    voltage = json_data["voltage"]

    if voltage <= 11.8:
        logging.warn("Voltage is low : {voltage}V > Warning")
        client.publish("information_panel/" + INFORMATION_PANEL_ID + "/command/warning", '{"enable":true}')
    
    point = Point("irrigation_system") \
        .tag("device", IRRIGATION_SYSTEM_ID) \
        .field("voltage", voltage) \
        .time(datetime.now(timezone.utc))
    userdata["influxdb"].write(bucket=BUCKET, org=ORG, record=point)

def recv_event_watering(client, userdata, msg):
    json_data = json.loads(msg.payload.decode()) 
    water_volume = json_data["volume"]

    if water_volume <= 0.1:
        logging.warning(f"Water Volume is Low : {water_volume}L > Warning")
        client.publish("information_panel/" + INFORMATION_PANEL_ID + "/command/warning", '{"enable":true}')
    else:
        ttl = seconds_until_midnight()
        logging.info(f"Watering Event Ok ttl:{str(ttl)} > Information")
        data = '{"enable":true, "ttl":' + str(ttl) + '}'
        client.publish("information_panel/" + INFORMATION_PANEL_ID + "/command/info", data)

    point = Point("irrigation_system") \
        .tag("device", IRRIGATION_SYSTEM_ID) \
        .field("water_volume", water_volume) \
        .time(datetime.now(timezone.utc))
    userdata["influxdb"].write(bucket=BUCKET, org=ORG, record=point)
    
def recv_status(client, userdata, msg):
    global last_status_update_time

    json_data = json.loads(msg.payload.decode()) 
    status = json_data["status"]

    if status == "close":
        logging.warning("IR Close > Warning")
        client.publish("information_panel/" + INFORMATION_PANEL_ID + "/command/warning", '{"enable":true}')
    elif status == "ok":
        last_status_update_time = int(time.time())

def main():
    global last_status_update_time
    global info_panel_update_time

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout  # 標準出力を明示的に指定
    )

    logging.info("Start IoT Controller")
    logging.info("Initialize")

    # InfluxDB
    influxdb_client = InfluxDBClient(url=INFLUXDB_URL, token=TOKEN, org=ORG)
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
 
    # mqtt
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.user_data_set({"influxdb": write_api})

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    except Exception as e:
        logging.error(f"Error connecting to broker: {e}")
        return

    client.loop_start()

    last_status_update_time = int(time.time())

    while True:
        # 10分間毎にHealth送信
        if ((info_panel_update_time + (10 * 60)) < int(time.time())):
            logging.info("Publish Health")
            client.publish("iot_controller/" + IOT_CONTROLLER_ID + "/status", '{"status":"ok"}')
            info_panel_update_time = int(time.time())

        # 30分間応答がない場合はwarning       
        if ((last_status_update_time + (30 * 60)) < int(time.time())):
            logging.warning(f"Un Healthy  > Warning")
            client.publish("information_panel/" + INFORMATION_PANEL_ID + "/command/warning", '{"enable":true}')
            last_status_update_time = int(time.time())
        time.sleep(1)

def signal_handler(sig, frame):
    logging.info(f"Signal received:{sig}")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    main()

