# Gemmas Book Manager

## Requirements

* Docker

## Install

1. Clone repo

```sh
git clone https://github.com/techkid889/gemmasbookmanagement.git
```

2. build with Docker

```sh
docker build .
```

3. run docker container with flags and match folders to corresponding locations

/app/downloads/ = Download Location
/app/books/ = Book Location
/config/ = Temp / Config Folder

```sh
docker run --name gemmasbookuploader -p 8000:5000 -v /Z/Downloads_Folder/:/app/downloads -v /Z/Books_Folder/:/app/books -v /config/:/config  gemmasbookuploader
```

or quick install with [Docker Hub](https://hub.docker.com/r/techkid889/gemmasbookmanagement)

```sh
docker pull techkid889/gemmasbookmanagement
```

## Usage

Upload books. See library. Modify Metadata.
