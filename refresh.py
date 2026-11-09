#!/usr/bin/env python3
"""Refresca data.json con el snapshot GTFS-RT mas reciente de Metrobus CDMX.

Uso:
    METROBUS_API_USER=... METROBUS_API_PASS=... python3 refresh.py

Lee las credenciales SOLO de variables de entorno. Nunca las escribas en
este archivo, en data.json, en logs ni en el repositorio. El script:
  1. Valida el acceso con POST /gtfs-api/partnerValidation.
  2. Descarga el .proto en tiempo real desde la URL temporal (3 h) que devuelve.
  3. Decodifica las posiciones de los vehiculos (GTFS-Realtime).
  4. Actualiza data.json (feed_timestamp, vehicles, conteos por linea).

El GTFS estatico (estaciones, rutas) ya esta en data.json y cambia poco;
este script no lo vuelve a descargar.
"""

import datetime
import json
import os
import sys
import urllib.request

API_URL = "https://metrobus-gtfs.sinopticoplus.com/gtfs-api/partnerValidation"
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
MEXICO_TZ = datetime.timezone(datetime.timedelta(hours=-6))


def post_validation(user, password):
    body = json.dumps({"usuario": user, "senha": password}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"partnerValidation devolvio HTTP {resp.status}")
        return json.loads(resp.read().decode())


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mblivemx-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def decode_vehicles(blob):
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(blob)
    vehicles = []
    counts = {"vehicle": 0, "trip_update": 0, "alert": 0}
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            counts["vehicle"] += 1
            v = entity.vehicle
            vehicles.append(
                {
                    "id": entity.id,
                    "vehicle_id": v.vehicle.id,
                    "label": v.vehicle.label,
                    "route_id": v.trip.route_id,
                    "trip_id": v.trip.trip_id,
                    "start_time": v.trip.start_time,
                    "start_date": v.trip.start_date,
                    "lat": v.position.latitude,
                    "lon": v.position.longitude,
                    "bearing": v.position.bearing,
                    "speed": v.position.speed,
                    "timestamp": v.timestamp,
                    "stop_id": v.stop_id,
                    "status": v.current_status,
                }
            )
        if entity.HasField("trip_update"):
            counts["trip_update"] += 1
        if entity.HasField("alert"):
            counts["alert"] += 1
    return feed.header.timestamp, vehicles, counts


def main():
    user = os.environ.get("METROBUS_API_USER")
    password = os.environ.get("METROBUS_API_PASS")
    if not user or not password:
        print(
            "Faltan METROBUS_API_USER y/o METROBUS_API_PASS en el entorno.",
            file=sys.stderr,
        )
        return 2

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    route_line = {r["route_id"]: r["line"] for r in data["routes"]}

    validation = post_validation(user, password)
    blob = download(validation["urlRealTime"])
    header_ts, raw_vehicles, counts = decode_vehicles(blob)

    # Solo posiciones validas en CDMX; se descartan 0,0 y pruebas fuera de rango.
    valid = [
        v
        for v in raw_vehicles
        if 19.0 <= v["lat"] <= 19.6 and -99.4 <= v["lon"] <= -98.9
    ]
    vehicles = []
    for v in valid:
        vehicles.append(
            {
                "id": v["vehicle_id"],
                "label": v["label"],
                "route_id": v["route_id"],
                "line": route_line.get(v["route_id"], ""),
                "lat": round(v["lat"], 6),
                "lon": round(v["lon"], 6),
                "speed": v["speed"],
                "start_time": v["start_time"],
            }
        )

    cst = datetime.datetime.fromtimestamp(header_ts, MEXICO_TZ)
    data["feed_timestamp"] = cst.strftime("%Y-%m-%dT%H:%M:%S-06:00")
    data["vehicles_total"] = len(vehicles)
    data["vehicles"] = vehicles
    per_line = {}
    for v in vehicles:
        if v["line"]:
            per_line[v["line"]] = per_line.get(v["line"], 0) + 1
    for line in data["lines"]:
        line["vehicles"] = per_line.get(line["line"], 0)

    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp_path, DATA_PATH)

    print(
        f"OK feed={data['feed_timestamp']} entidades={counts} "
        f"validos={len(vehicles)} descartados={len(raw_vehicles) - len(vehicles)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
