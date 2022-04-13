# GTFS and GTFS Realtime feed generator toolkit for DPMP

Toolkit to create and maintain [GTFS](https://gtfs.org/schedule/) and
[GTFS Realtime](https://gtfs.org/realtime/) feeds for Pardubice public
transportation.

It aims to provide a bridge between (semi-)propriatary data formats and
standard transit open data for publication to Google as well as general
analysis.

*Note*: still a work in progress.

## How this works?

This tool bundle builds beforementioned feeds out of [CIS data](https://portal.cisjr.cz), bus stop geo coordinates
in DPMP proprietary format and also REST API that provides latest vehicle locations and deviations from the schedule.

The static data (GTFS) needs to be updated whenever bus schedule changes. Not so often.

The realtime data (GTFS - Realtime) needs to be updates as often as possible so that feed consumers (and ultimately
passengers) don't end up with stale info. Ideally, you should rebuilt the feed with same frequency buses send their
location updates. At the time of this writing, this would be something like every 15 seconds.

General workflow is following:

1. Create GTFS feed out of CIS data and bus stop coords. Update it when schedule changes.
2. Create & frequently update GTFS-Realtime feed using GTFS feed and realtime API as input.

Both feeds have to be exposed publicly to let consumers grab them at will. Exposing the feeds is out of scope of this
toolkit but should be fairly simple using [NGINX](https://www.nginx.com) for example.

In order to integrate Google, an agency representative has to register the feed URLs as well.

To start using this tool bundle, you'll first need to get hold of following stuff:

- Transit agency data in a [JDF format](https://www.dpmo.cz/doc/cz/jdf-1.10.pdf) (accepted by CIS). Extract it and put
  it somewhere on your filesystem wrapped in `jdf/1/` so that you have files like `jdf/1/Spoje.txt`.
- Stop location geodata in raw form (`STANICE.ZS`).
- An API key for the MHD REST API. Ask DPMP representatives to provide you with one.

## Using Docker

If you don't want to hassle with installing .NET or Python, there are prebuilt Docker images you can use easily.

1. Copy over JDF source and `STANICE.ZS` to a single parent directory, let' say `/tmp/data` and `cd` into it:

    ```sh
    cd /tmp/data
    ```

2. Prepare stop location CSV to feed `jrutil` later on:

    ```sh
    docker run -v $PWD:/data xaralis/dpmp-gtfs-bridge:latest ./convert-stop-locations.sh  --src_file /data/STANICE.ZS --dest_file /data/stop_locations.csv
    ```

    This will create `/tmp/data/stop_locations.csv`.

3. Convert JDF feed to GTFS using `jrutil`:

    ```
    mkdir gtfs-out
    docker run -v $PWD:/data xaralis/dpmp-gtfs-jrutil:latest dotnet run -- jdf-to-gtfs --stop-coords-by-id /data/stop_locations.csv /data/jdf/1 /data/gtfs-out
    ```

    This will create your GTFS feed in `/tmp/data/gtfs-out`. You should re-run this command whenever your transi
    schedule changes.

4. Start GTFS Realtime daemon:

    ```sh
    docker run -it -v $PWD:/data xaralis/dpmp-gtfs-bridge:latest ./start-gtfsr-generator.sh --mhd_api_key=[API_KEY] --gtfs_trips_src_file=/data/gtfs-out/trips.txt --dest_file=/data/gtfs-out/gtfsr.pb
    ```

    The daemon is meant to be up all the time as the realtime feed needs to be fresh.

## Running directly

1. Install & build [jrutil](https://gitlab.com/dvdkon/jrutil) locally, follow instructions at the library home page.
   Simply put: you'll need to install .NET support (v5) on your machine and also clone linked repositories in
   the `thirdparty` directory (refrer to `Dockerfile.jrutil` for details). Then build the `jrutil-multitool`:

    ```sh
    dotnet build jrutil-multitool
    ```

2. Install this app and its dependencies:

    ```sh
    git clone git@github.com:xaralis/dpmp-gtfs.git && cd dpmp-gtfs
    poetry install
    ```

3. Prepare stop location CSV to feed `jrutil` later on:

    ```sh
    poetry run src/convert_stop_locations.py --src_file STANICE.ZS
    ```

4. Convert JDF feed to GTFS using `jrutil`:

    ```sh
    cd path/to/jrutil/jrutil-multitool
    dotnet run -- jdf-to-gtfs --stop-coords-by-id path/to/stop_locations.csv path/to/jdf/1 path/to/gtfs/output/dir
    ```

    This will create your GTFS feed in specified location. You should re-create the feed whenever your transit
    schedule changes.

5. Start GTFS Realtime daemon:

    ```sh
    cd path/to/dpmp-gtfs
    poetry run src/generate_gtfs_realtime.py --mhd_api_key=[API_KEY] --gtfs_trips_src_file=path/to/gtfs/output/dir/trips.txt --dest_file=path/to/gtfs/output/dir//gtfsr.pb
    ```

    The daemon is meant to be up all the time as the realtime feed needs to be fresh. Refer to further config options
    with:

    ```
    poetry run src/generate_gtfs_realtime.py --help
    ```

## Verifying GTFS feed

First, create a Google Maps API key. Follow the official Google guide:

https://developers.google.com/maps/documentation/maps-static/get-api-key#creating-api-keys

Now you can visualise the feed using Google's `transitfeed` toolkit. I've added some basic fixes as the original
repository is old and unmaintained. Now, assuming your previously generated GTFS feed lives at `/tmp/data/gtfs-out`,
you can run the schedule viewer with this command:

```sh
docker run -it -v ~/tmp/data/gtfs-out:/data -p 8765:8765 xaralis/dpmp-gtfs-transitfeed:latest python schedule_viewer.py --key [API_KEY] --feed_filename /data
```

After couple seconds, this will expose the schedule viewer web app on [http://localhost:8765](http://localhost:8765).
