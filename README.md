insave
======

Save Instagram feed locally.

### Usage

   $ python2 insave.py --help
   usage: insave.py [-h] [-p PATH] [-u USERID] [-c COUNT] [-q] [-l LOG] [-t TOKEN]

   Save instagram feed locally

   optional arguments:
     -h, --help            show this help message and exit
     -p PATH, --path PATH  path to saved media (default: media)
     -u USERID, --userid USERID
                           user id (not name) (default: 46764821)
     -c COUNT, --count COUNT
                           number of recent medias to save (default: 10)
     -q, --quiet           do not print to stdout (default: False)
     -l LOG, --log LOG     log to file (default: None)
     -t TOKEN, --token TOKEN
                           path to access token file (default: token)

This is how I run it in cron:

   # save instagram feed
   0 * * * * cd /home/bz/prg/src/bz/python/insave && \
      python2 insave.py --path ~/share/dropbox/Dropbox/pics/insave \
      --count 50 --log /var/log/insave.log --token token

### Dependencies

- requests
- [python-instagram](https://github.com/Instagram/python-instagram)

### Author

(c) 2014 Yuri Bochkarev
