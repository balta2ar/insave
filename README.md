insave
======

Save Instagram feed locally.

### Usage

```
usage: insave.py [-h] [-p PATH] [-u USERID] [-d DOWNLOAD] [-s SKIP]
                 [-f FETCH] [-q] [-l LOG] [-t TOKEN]

Save instagram feed locally

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  path to saved media (default: media)
  -u USERID, --userid USERID
                        user id (not name) (default: 46764821)
  -d DOWNLOAD, --download DOWNLOAD
                        number of recent medias to download before termination (default: 100)
  -s SKIP, --skip SKIP  number of recent medias to skip CONTINUOUSLY before termination (default: 100)
  -f FETCH, --fetch FETCH
                        number of medias to ask in each API request (default: 100)
  -q, --quiet           do not print to stdout (default: False)
  -l LOG, --log LOG     log to file (default: None)
  -t TOKEN, --token TOKEN
                        path to access token file (default: token)
```

This is how I run it in cron:
```
# save instagram feed every hour
0 * * * * cd /home/bz/prg/src/bz/python/insave && \
    python2 insave.py --path ~/pictures/dropbox/insave \
    --download 10000 --skip 100 --fetch 100 --log \
    /var/log/insave.log > /dev/null
```

### Dependencies

- [requests](https://github.com/kennethreitz/requests)

### Author

(c) 2014-2017 Yuri Bochkarev
