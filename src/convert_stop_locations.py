#!/usr/bin/env python3
import argparse
from collections import defaultdict
import csv
from io import TextIOWrapper
from typing import List, MutableMapping, NamedTuple, Optional, Sequence
from decimal import Decimal


class IntermediaryLocation(NamedTuple):
    seqnr: str
    name: str
    lat: Decimal
    lon: Decimal


class OutLocation(NamedTuple):
    fullid: str
    lat: str
    lon: str

    @classmethod
    def from_intermediary(cls, fullid: str, intermediary: IntermediaryLocation):
        return cls(fullid=fullid, lat=intermediary.lat, lon=intermediary.lon)


def _build_id(id_prefix: Optional[str], *bits: str):
    return "-".join((id_prefix, *bits) if id_prefix is not None else bits)


def parse_stops(f: TextIOWrapper, id_prefix: Optional[str]):
    by_root_id: MutableMapping[str, List[OutLocation]] = defaultdict(list)

    for line in f.readlines():
        fullid, name, lon, lat = line.split("\t")

        if lat and lon:
            lat = lat.replace(",", ".")
            lon = lon.replace(",", ".")
            baseid, seqnr = fullid[:4].lstrip("0"), fullid[4:].lstrip("0")
            by_root_id[baseid].append(
                IntermediaryLocation(
                    seqnr=seqnr, name=name, lat=Decimal(lat), lon=Decimal(lon)
                )
            )

    stops: List[OutLocation] = []

    for baseid, locations in by_root_id.items():
        stops.append(
            OutLocation.from_intermediary(_build_id(id_prefix, baseid), locations[0])
        )

        for loc in locations:
            stops.append(
                OutLocation.from_intermediary(
                    _build_id(id_prefix, baseid, loc.seqnr), loc
                )
            )

    return stops


def write_to_csv(f: TextIOWrapper, stop_locations: Sequence[OutLocation]):
    writer = csv.writer(f)

    for sl in stop_locations:
        writer.writerow((sl.fullid, sl.lat, sl.lon))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare CSV files with stop locations suitable to use with jrutil."
    )
    parser.add_argument(
        "--id_prefix",
        help="Prefix to prepend to stop identifier, make sure to use the same jrutil does.",
        default="JDFS",
    )
    parser.add_argument(
        "--src_file",
        type=argparse.FileType("r", encoding="windows-1250"),
        help="The file to read stop locations from, e.g. STANICE.ZS. Should be in windows-1250 encoding.",
    )
    parser.add_argument(
        "--dest_file",
        type=argparse.FileType("w", encoding="utf8"),
        help="The file to write stop locations to, e.g stop_locations.csv.",
        default="stop_locations.csv",
    )
    args = parser.parse_args()

    if args.src_file:
        stop_locations = parse_stops(f=args.src_file, id_prefix=args.id_prefix)
        write_to_csv(f=args.dest_file, stop_locations=stop_locations)
    else:
        parser.print_usage()
