#!/usr/bin/env python3
import argparse
import csv
from datetime import datetime, timedelta
import json
import logging
import re
import time
from typing import NamedTuple, Sequence

from google.transit import gtfs_realtime_pb2 as gtfsr
from pytz import timezone
import requests

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('{asctime} {levelname:>8s} {message}', style='{'))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger()

delay_regexp = re.compile(r"^-?(?P<hours>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})$")
prague_tz = timezone("Europe/Prague")


class GTFSTripInfo(NamedTuple):
    route_id: str
    trip_id: str
    trip_short_name: str
    service_id: str


class TripIndex:
    def __init__(self, line_nr_prefix: str, trips: Sequence[GTFSTripInfo]):
        def _key(trip_short_name: str):
            n = trip_short_name.removeprefix(line_nr_prefix)
            line_nr, connection_no = n.split(" ")
            return (int(line_nr), int(connection_no))

        self.trips = {_key(t.trip_short_name): t for t in trips}

    def get_by_line_nr_and_connection_no(self, line_nr: int, connection_no: int):
        return self.trips[(line_nr, connection_no)]


def load_trips(src_pth: str) -> Sequence[GTFSTripInfo]:
    with open(src_pth, "r", encoding="utf8") as f:
        for idx, line in enumerate(csv.reader(f, delimiter=",", quotechar='"')):
            if idx == 0:
                continue

            route_id, service_id, trip_id, _, trip_short_name, *_ = line

            yield GTFSTripInfo(
                route_id=route_id,
                trip_id=trip_id,
                trip_short_name=trip_short_name,
                service_id=service_id,
            )


def get_api_buses(api_root: str, api_key: str):
    r = requests.post(f"{api_root}/buses", data=json.dumps({"key": api_key}))
    return r.json()["data"]


def refresh_feed(
    line_nr_prefix: str,
    trips_src_path: str,
    dest_path: str,
    mhd_api_root: str,
    mhd_api_key: str,
):
    logger.info('Refreshing feed')

    trip_index = TripIndex(
        line_nr_prefix=line_nr_prefix, trips=load_trips(trips_src_path)
    )
    gtfsr_feed = gtfsr.FeedMessage()

    gtfsr_feed.header.gtfs_realtime_version = "2.0"
    gtfsr_feed.header.timestamp = int(time.time())

    for idx, businfo in enumerate(get_api_buses(mhd_api_root, mhd_api_key)):
        line_name = int(businfo["line_name"])
        connection_no = int(businfo["connection_no"])
        state_valid_at = datetime.strptime(
            businfo["state_dtime"], "%Y-%m-%d %H:%M:%S"
        ).astimezone(tz=prague_tz)

        if businfo["time_difference"]:
            delay_dir = -1 if businfo["time_difference"].startswith("-") else 1
            delay_parts = delay_regexp.match(businfo["time_difference"])

            if delay_parts:
                delay_secs = (
                    timedelta(
                        hours=int(delay_parts["hours"]),
                        minutes=int(delay_parts["minutes"]),
                        seconds=int(delay_parts["seconds"]),
                    ).seconds
                    * delay_dir
                )
            else:
                logger.warning(
                    f'Could not determine bus delay from {businfo["time_difference"]}'
                )
                continue
        else:
            delay_secs = 0

        try:
            trip_info = trip_index.get_by_line_nr_and_connection_no(
                line_name, connection_no
            )

            gtfsr_trip_descriptor = gtfsr.TripDescriptor(
                trip_id=trip_info.trip_id, route_id=trip_info.route_id
            )
            gtfsr_vehicle_descriptor = gtfsr.VehicleDescriptor(id=businfo["vid"])

            gtfsr_vehicle_position = gtfsr.VehiclePosition(
                trip=gtfsr_trip_descriptor,
                vehicle=gtfsr_vehicle_descriptor,
                position=gtfsr.Position(
                    latitude=businfo["gps_latitude"],
                    longitude=businfo["gps_longitude"],
                    bearing=businfo["gps_course"],
                ),
            )

            gtfsr_trip_update = gtfsr.TripUpdate(
                trip=gtfsr_trip_descriptor,
                vehicle=gtfsr_vehicle_descriptor,
                timestamp=int(state_valid_at.timestamp()),
                delay=delay_secs,
            )

            gtfsr_feed.entity.add(
                id=str(idx),
                vehicle=gtfsr_vehicle_position,
                trip_update=gtfsr_trip_update,
            )
        except KeyError:
            # Trip not specified in GTFS
            logger.warning(
                f"TripInfo for line_name={line_name} and connection_no={connection_no} not found in GTFS feed"
            )

    with open(dest_path, "wb") as f:
        f.write(gtfsr_feed.SerializeToString())

    logger.info(f'Feed refreshed at {gtfsr_feed.header.timestamp}, {len(gtfsr_feed.entity)} entities in total')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run periodic GTFS-Realtime feed build"
    )
    parser.add_argument(
        "--line_nr_prefix",
        help="Prefix to strip from GTFS trip short name when matching against MHD API output",
        default="6550",
    )
    parser.add_argument("--mhd_api_key", help="MHD realtime API key")
    parser.add_argument(
        "--mhd_api_root",
        help="Root URL of MHD API, e.g. https://mhd.kacis.eu/api",
        default="https://mhd.kacis.eu/api",
    )
    parser.add_argument(
        "--gtfs_trips_src_file",
        help="The GTFS trips.txt file location",
    )
    parser.add_argument(
        "--dest_file",
        help="The GTFS-Realtime output file location",
        default="gtfs.pb",
    )
    parser.add_argument(
        "--refresh_period_secs",
        help="How often should the feed be refreshed in seconds",
        default=10,
    )

    args = parser.parse_args()

    if args.mhd_api_key and args.gtfs_trips_src_file:
        try:
            while True:
                try:
                    refresh_feed(
                        line_nr_prefix=args.line_nr_prefix,
                        trips_src_path=args.gtfs_trips_src_file,
                        dest_path=args.dest_file,
                        mhd_api_key=args.mhd_api_key,
                        mhd_api_root=args.mhd_api_root,
                    )
                except Exception:
                    logger.exception("Could not refresh the feed")
                finally:
                    time.sleep(args.refresh_period_secs)
        except KeyboardInterrupt:
            logger.info("Bye")
    else:
        parser.print_usage()
