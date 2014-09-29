import os
import logging
import requests
import argparse
from os.path import join as J
from instagram.client import InstagramAPI


LOGLEVEL = logging.INFO
FORMAT = '%(asctime)s %(process)s %(name)s %(levelname)-8s - %(message)s'
_log = logging.getLogger('insave')


class InSave(object):
    def __init__(self, api, user_id, download, skip, fetch):
        self._api = api
        self._user_id = user_id
        self._downloaded = 0
        self._skipped = 0
        self._download = download
        self._skip = skip
        self._fetch = fetch

    def show_stats(self):
        _log.info('Saved: %d, skipped: %d, total: %d',
                  self._downloaded, self._skipped, self._downloaded + self._skipped)

    @staticmethod
    def _name(media):
        return '{0}-{1}-{2}.jpg'.format(media.created_time.isoformat(),
                                        media.user.username,
                                        media.id)

    def _save_media(self, name, url):
        if os.path.exists(name):
            _log.debug('Already downloaded, skipping')
            self._skipped += 1
            return False
        _log.info('Downloading to %s', os.path.basename(name))
        try:
            os.makedirs(os.path.dirname(name))
        except OSError:
            pass  # dir already exists, probably
        r = requests.get(url)
        with open(name, 'wb') as f:
            f.write(r.content)
        self._downloaded += 1
        self._skiped = 0
        return True

    @property
    def _within_limits(self):
        return (self._downloaded < self._download and
                self._skipped < self._skip)

    def save(self, path):
        recent, next_ = self._api.user_media_feed(user_id=self._user_id,
                                                  count=self._fetch)
        while (next_ or recent):
            _log.debug('Received %d medias', len(recent))
            for media in recent:
                if not self._within_limits:
                    return
                if media.type != 'image':
                    _log.debug('Skipping non-image')
                    continue
                name = J(path, InSave._name(media))
                url = media.get_standard_resolution_url()
                self._save_media(name, url)
            recent, next_ = self._api.user_media_feed(with_next_url=next_)


def init_log(args):
    _log.setLevel(LOGLEVEL)
    formatter = logging.Formatter(FORMAT)
    if args.log is not None:
        h = logging.FileHandler(args.log)
        h.setLevel(LOGLEVEL)
        h.setFormatter(formatter)
        _log.addHandler(h)
    if not args.quiet:
        h = logging.StreamHandler()
        h.setLevel(LOGLEVEL)
        h.setFormatter(formatter)
        _log.addHandler(h)


def parse_args():
    parser = argparse.ArgumentParser(description='Save instagram feed locally',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--path', default='media', help='path to saved media')
    parser.add_argument('-u', '--userid', default='46764821', help='user id (not name)')
    parser.add_argument('-d', '--download', default=100, type=int, help='number of recent medias to download before termination')
    parser.add_argument('-s', '--skip', default=100, type=int, help='number of recent medias to skip CONTINUOUSLY before termination')
    parser.add_argument('-f', '--fetch', default=100, type=int, help='number of medias to ask in each API request')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='do not print to stdout')
    parser.add_argument('-l', '--log', default=None, help='log to file')
    parser.add_argument('-t', '--token', default='token', help='path to access token file')
    args = parser.parse_args()
    args.path = os.path.expanduser(os.path.expandvars(args.path))
    init_log(args)
    return args


def main():
    args = parse_args()

    _log.info('Saving %d (skip %d, fetch %d) of userid %s feed medias to %s',
              args.download, args.skip, args.fetch, args.userid, args.path)
    access_token = open(args.token).read().strip()
    api = InstagramAPI(access_token=access_token)
    saver = InSave(api, args.userid, args.download, args.skip, args.fetch)
    saver.save(args.path)
    saver.show_stats()


if __name__ == '__main__':
    main()
