# iot_home

## IoT機材を家庭で使う際に一式を導入するDocker Compose

- Mosquitto
  - MQTTブローカー
- InfluxDB
  - 時系列DB
- Grafana
  - ビジュアライズダッシュボード
- iot_controller
  - IoT機器を集中管理するプログラム
  - Python

## 使い方

Dockerが動作する環境で実行する必要があります。

```sh
$ docker compose up -d # 起動
```

初期パスワードは docker-composeを参照
Grafanaは http://localhost:3000/ 
GrafanaからInfluxDBを参照する際は influxdb:8086 で接続が可能。


## Grafana向けFluxクエリ例

```flux
from(bucket: "iothomebucket")
|> range(start: v.timeRangeStart, stop: v.timeRangeStop)
|> filter(fn: (r) => r._measurement == "irrigation_system")
|> filter(fn: (r) => r["_field"] == "voltage")
|> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)

```

```flux
from(bucket: "iothomebucket")
|> range(start: v.timeRangeStart, stop: v.timeRangeStop)
|> filter(fn: (r) => r._measurement == "irrigation_system")
|> filter(fn: (r) => r["_field"] == "water_volume")
|> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

## MQTT
irrigation_system/0001/status
{"status":"ok"}

irrigation_system/0001/telemetry/voltage
{"voltage":12.4}

irrigation_system/0001/events/watering
{"volume":5.1}

