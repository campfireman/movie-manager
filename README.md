# Movie manager

CLI-tool for managing a master movie table.

## Features

### Merging

### Augmenting

## Setup

The default setting uses a local IMDB database as backend, as the Web based search is very slow. Follow the instructions on [Cinemagoer](https://imdbpy.readthedocs.io/en/latest/usage/s3.html)

To create a local postgres database run:

```[bash]
sudo docker-compose up
```

Then you can use:

```[bash]
python3 /path/to/s32cinemagoer.py /path/to/imdb_data/ postgresql://postgres:postgres@0.0.0.0:5432/imdb
```
