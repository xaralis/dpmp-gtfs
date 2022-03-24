# GTFS and GTFS Realtime feed generator toolkit for DPMP

This is just a bunch of utils to create and maintain GTFS and GTFS feeds
for Pardubice public transportation.

It aims to provide a bridge between (semi-)propriatary data formats and
standard transit open data for publication to Google as well as general
analysis.

This is still a work in progress.

## Creating a GTFS feed

1. Acquire transit agency data in a JDF format (accepted by CIS). Extract it and put it somewhere on your filesystem wrapped in `jdf/1/` so that you have files like `jdf/1/Spoje.txt`.
2. Acquire stop location geodata in raw form (`STANICE.ZS`).
3. Install [jrutil](https://gitlab.com/dvdkon/jrutil) locally, we'll use it to convert CIS feed to GTFS. You'll also need to install .NET support on your machine, follow official docs to do so.
4. Install this app and it's dependencies:

    ```sh
    poetry install
    ```

5. Prepare stop location CSV to feed `jrutil` later on:

    ```sh
    # Will create ./stop_locations.csv
    poetry run convert_stop_locations.py --src_file STANICE.ZS
    ```

6. Convert JDF feed to GTFS using `jrutil`:

    ```sh
    cd path/to/jrutil/jrutil-multitool
    dotnet run -- jdf-to-gtfs --stop-coords-by-id path/to/stop_locations.csv path/to/jdf/1 path/to/gtfs/output/dir
    ```

This will create your GTFS feed in specified location. You should re-create the feed whenever your transit schedule changes.

## Maintain a GTFS Realtime feed

This works with realtime API published by DPMP recently. It will create another feed - GTFS Realtime - that contains
realtime transit updates such as delays and bus geo locations.

In order to run the deamon that refreshes the feed, you'll need GTFS feed from
the preivous step already compiled. You'll also need an API key, ask the DPMP to
provide you one. Once you have those, simply run:

```sh
poetry run ./generate_gtfs_realtime.py --mhd_api_key=[API_KEY] --gtfs_trips_src_file=paht/to/gtfs/output/dir
```

This will start a deamon that recreates the GTFS Realtime feed periodically. Also refer to furt config options with:

```
poetry run ./generate_gtfs_realtime.py --help
```


