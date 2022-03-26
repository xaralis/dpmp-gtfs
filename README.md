# GTFS and GTFS Realtime feed generator toolkit for DPMP

This is just a bunch of utils to create and maintain GTFS and GTFS feeds
for Pardubice public transportation.

It aims to provide a bridge between (semi-)propriatary data formats and
standard transit open data for publication to Google as well as general
analysis.

This is still a work in progress. I aim to bundle all this inside Docker to make
it a one-liner. Until then, you'll have to proceed manually.


## Prerequisites

1. Acquire transit agency data in a JDF format (accepted by CIS). Extract it and put it somewhere on your filesystem
   wrapped in `jdf/1/` so that you have files like `jdf/1/Spoje.txt`.
2. Acquire stop location geodata in raw form (`STANICE.ZS`).

## Running using Docker

If you don't want to hassle with installing .NET or Python, you can run the tools using Docker only. It is the
recommended way to use this.

### Creating a GTFS feed

1. Copy over JDF source and `STANICE.ZS` to a single parent directory, let' say `/tmp/data` and `cd` into it:

    ```sh
    mkdir -p /tmp/data && cd /tmp/data
    ```

1. Prepare stop location CSV to feed `jrutil` later on:

    ```sh
    docker run -v $PWD:/data xaralis/dpmp-gtfs-bridge:latest ./convert-stop-locations.sh  --src_file /data/STANICE.ZS --dest_file /data/stop_locations.csv
    ```

    This will create `/tmp/data/stop_locations.csv`.

2. Convert JDF feed to GTFS using `jrutil`:

    ```
    mkdir gtfs-out
    docker run -v $PWD:/data xaralis/dpmp-gtfs-jrutil:latest dotnet run -- jdf-to-gtfs --stop-coords-by-id /data/stop_locations.csv /data/jdf/1 /data/gtfs-out
    ```

This will create your GTFS feed in specified location. You should re-create the feed whenever your transit schedule changes.

### Maintain a GTFS Realtime feed

This works with realtime API published by DPMP recently. It will create another feed - GTFS Realtime - that contains
realtime transit updates such as delays and bus vehicle position geo coordinates.

In order to run the deamon that refreshes the feed, you'll need the GTFS feed from
the preivous step already compiled. You'll also need an API key for the MHD REST API. Ask DPMP representatives to
provide you with one.

Once you have all the prerequisites at hand, simply run:

```sh
docker run -v $PWD:/data xaralis/dpmp-gtfs-bridge:latest ./start-gtfsr-generator.sh  --mhd_api_key=[API_KEY] --gtfs_trips_src_file=/data/gtfs-out
```

This will start a deamon that recreates the GTFS Realtime feed periodically. The daemon is meant to be up all the time
as the realtime feed needs to be fresh.

## Running directly

### Creating a GTFS feed

1. Install & build [jrutil](https://gitlab.com/dvdkon/jrutil) locally, we'll use it to convert CIS feed to GTFS. You'll also need to install .NET support on your machine, follow official docs to do so.
2. Install this app and it's dependencies:

    ```sh
    poetry install
    ```

3. Prepare stop location CSV to feed `jrutil` later on:

    ```sh
    # Will create ./stop_locations.csv
    poetry run src/convert_stop_locations.py --src_file STANICE.ZS
    ```

4. Convert JDF feed to GTFS using `jrutil`:

    ```sh
    cd path/to/jrutil/jrutil-multitool
    dotnet run -- jdf-to-gtfs --stop-coords-by-id path/to/stop_locations.csv path/to/jdf/1 path/to/gtfs/output/dir
    ```

This will create your GTFS feed in specified location. You should re-create the feed whenever your transit schedule changes.

### Maintain a GTFS Realtime feed

This works with realtime API published by DPMP recently. It will create another feed - GTFS Realtime - that contains
realtime transit updates such as delays and bus vehicle position geo coordinates.

In order to run the deamon that refreshes the feed, you'll need the GTFS feed from
the preivous step already compiled. You'll also need an API key for the MHD REST API. Ask DPMP representatives to
provide you with one.

Once you have all the prerequisites at hand, simply run:

```sh
poetry run src/generate_gtfs_realtime.py --mhd_api_key=[API_KEY] --gtfs_trips_src_file=path/to/gtfs/output/dir
```

This will start a deamon that recreates the GTFS Realtime feed periodically. The daemon is meant to be up all the time
as the realtime feed needs to be fresh.

Refer to further config options with:

```
poetry run src/generate_gtfs_realtime.py --help
```
