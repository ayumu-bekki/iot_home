# iot_home


## Grafana向けFluxクエリ例
from(bucket: "iothomebucket")
|> range(start: v.timeRangeStart, stop: v.timeRangeStop)
|> filter(fn: (r) => r._measurement == "irrigation_system")
|> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
