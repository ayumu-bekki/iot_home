
irrigation_system/0001/status
{"status":"ok"}

irrigation_system/0001/telemetry/voltage
{"voltage":12.4}

irrigation_system/0001/events/watering
{"volume":5.1}

from(bucket: "iothomebucket")
|> range(start: v.timeRangeStart, stop: v.timeRangeStop)
|> filter(fn: (r) => r._measurement == "irrigation_system")
|> filter(fn: (r) => r["_field"] == "voltage")
|> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)


from(bucket: "iothomebucket")
|> range(start: v.timeRangeStart, stop: v.timeRangeStop)
|> filter(fn: (r) => r._measurement == "irrigation_system")
|> filter(fn: (r) => r["_field"] == "water_volume")
|> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)

