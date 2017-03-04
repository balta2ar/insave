import os
import json
import logging
import requests
import argparse
from netrc import netrc
from datetime import datetime
from os.path import join as J
# from instagram.client import InstagramAPI


LOGLEVEL = logging.INFO
FORMAT = '%(asctime)s %(process)s %(name)s %(levelname)-8s - %(message)s'
_log = logging.getLogger('insave')


def enable_requests_debug():
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class InstaAPI(object):
    SHARED_DATA_SUBSTRING = '<script type="text/javascript">window._sharedData = {'

    def __init__(self):
        self._logged_in = False
        self._session = requests.Session()

    def _update_headers(self, csrftoken):
        headers = {'X-CSRFToken': csrftoken,
                   'Host': 'www.instagram.com',
                   'Origin': 'https://www.instagram.com',
                   'Referer': 'https://www.instagram.com/',
                   'X-Instagram-AJAX': '1',
                   'X-Requested-With': 'XMLHttpRequest',
                   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}
        self._session.headers.update(headers)

    def _login(self):
        login, _, password = netrc().hosts['instagram']
        credentials = {
            'username': login,
            'password': password
        }

        main_page = self._session.get('https://www.instagram.com/')
        csrftoken = main_page.cookies['csrftoken']
        self._update_headers(csrftoken)

        login_result = self._session.post(
            'https://www.instagram.com/accounts/login/ajax/',
            data=credentials)
        # print(login_result)
        main_page_again = self._session.get('https://www.instagram.com/')
        # print(main_page_again)

        if not InstaAPI.SHARED_DATA_SUBSTRING in main_page_again.content:
            _log.error('No line with sharedData in main page response (login)')
            _log.error(main_page_again.content)
            return False

        return True

    def _get_first_page(self):
        main_page = self._session.get('https://www.instagram.com/')
        csrftoken = main_page.cookies['csrftoken']
        self._update_headers(csrftoken)

        if not InstaAPI.SHARED_DATA_SUBSTRING in main_page.content:
            _log.error('No line with sharedData in main page response (first page)')
            _log.error(main_page.content)
            return None

        lines = [line for line in main_page.content.splitlines()
                 if InstaAPI.SHARED_DATA_SUBSTRING in line]

        # from ipdb import set_trace; set_trace(context=20)
        unparsed_feed = ''.join(lines)
        start = unparsed_feed.find('{')
        end = unparsed_feed.rfind('}')
        if (start == -1) or (end == -1):
            _log.error('Could not find start or end of JSON in sharedData (first page)')
            _log.error(unparsed_feed)
            return None

        feed = unparsed_feed[start:end+1]
        try:
            feed = json.loads(feed)
        except Exception as e:
            _log.error('Could not load JSON response (first page)')
            _log.error(feed)
            return None

        feed_page = feed['entry_data']['FeedPage'][0]
        return self._simplify_feed_first(feed_page)

    def _get_next_page(self, end_cursor):
        data = {
            'q': '''ig_me() {
  feed {
    media.after(%s, %s) {
      nodes {
        id,
        attribution,
        caption,
        code,
        comments.last(4) {
          count,
          nodes {
            id,
            created_at,
            text,
            user {
              id,
              profile_pic_url,
              username
            }
          },
          page_info
        },
        comments_disabled,
        date,
        dimensions {
          height,
          width
        },
        display_src,
        is_video,
        likes {
          count,
          nodes {
            user {
              id,
              profile_pic_url,
              username
            }
          },
          viewer_has_liked
        },
        location {
          id,
          has_public_page,
          name,
          slug
        },
        owner {
          id,
          blocked_by_viewer,
          followed_by_viewer,
          full_name,
          has_blocked_viewer,
          is_private,
          profile_pic_url,
          requested_by_viewer,
          username
        },
        usertags {
          nodes {
            user {
              username
            },
            x,
            y
          }
        },
        video_url,
        video_views
      },
      page_info
    }
  },
  id,
  profile_pic_url,
  username}
''' % (end_cursor, 12),
            'ref': 'feed::show',
            # 'query_id': "17854890973106267"
        }

        # enable_requests_debug()

        next_page = self._session.post('https://www.instagram.com/query/',
                                       data=data)

        # from ipdb import set_trace; set_trace(context=20)
        try:
            feed = json.loads(next_page.content)
        except Exception as e:
            _log.error('Cannot decode JSON for the next page')
            _log.error(next_page.status)
            _log.error(next_page.reason)
            _log.error(next_page.content)
            raise
        return self._simplify_feed_second(feed)

    def _simplify_feed_first(self, feed):
        with open('feed-first.json', 'w') as file_:
            json.dump(feed, file_, indent=4)
        media = feed['graphql']['user']['edge_web_feed_timeline']
        end_cursor = media['page_info']['end_cursor']

        simple = []
        for node in media['edges']:
            node = node['node']
            entry = {
                'username': node['owner']['username'],
                'username_id': node['owner']['id'],
                'date': node['taken_at_timestamp'],
                'is_video': node['is_video'],
                'post_id': node['id'],
                'url': node['display_url'],
            }
            simple.append(entry)

        return simple, end_cursor

    def _simplify_feed_second(self, feed):
        with open('feed-second.json', 'w') as file_:
            json.dump(feed, file_, indent=4)
        media = feed['feed']['media']
        end_cursor = media['page_info']['end_cursor']

        simple = []
        for node in media['nodes']:
            entry = {
                'username': node['owner']['username'],
                'username_id': node['owner']['id'],
                'date': node['date'],
                'is_video': node['is_video'],
                'post_id': node['id'],
                'url': node['display_src'],
            }
            simple.append(entry)

        return simple, end_cursor

    def user_media_feed(self, user_id=None, count=10, with_next_url=None):
        if not self._logged_in:
            self._logged_in = self._login()
            if not self._logged_in:
                _log.error('Could not login')
                return None, None

        if with_next_url is None:
            return self._get_first_page()
        else:
            return self._get_next_page(with_next_url)


class InSave(object):
    def __init__(self, api, user_id, download, skip, fetch):
        self._api = api
        self._user_id = user_id
        self._downloaded = 0
        self._skipped = 0
        self._total = 0
        self._download = download
        self._skip = skip
        self._fetch = fetch

    def show_stats(self):
        _log.info('Saved: %d, skipped: %d, total: %d',
                  self._downloaded, self._skipped, self._total)

    @staticmethod
    def _name(media):
        # Expected format:
        # timestamp-username-postid_userid.jpg
        # 2016-04-01T03:09:03-shaded_canvas-1218530217333611376_1489049085.jpg

        return '{0}-{1}-{2}-{3}.jpg'.format(
            datetime.fromtimestamp(media['date']).isoformat(),
            media['username'],
            media['post_id'],
            media['username_id']
        )

        #return '{0}-{1}-{2}.jpg'.format(media.created_time.isoformat(),
        #                                media.user.username,
        #                                media.id)

    def _save_media(self, name, url):
        if os.path.exists(name):
            _log.debug('Already downloaded, skipping')
            self._skipped += 1
            self._total += 1
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
        self._skipped = 0
        self._total += 1
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
                #if media.type != 'image':
                if media['is_video']:
                    _log.debug('Skipping non-image')
                    continue
                name = J(path, InSave._name(media))
                #url = media.get_standard_resolution_url()
                url = media['url']
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


def testweb():
    print('hello')

    login, _, password = netrc().hosts['instagram']
    credentials = {
        'username': login,
        'password': password
    }

    session = requests.Session()
    main_page = session.get('https://www.instagram.com/')
    csrftoken = main_page.cookies['csrftoken']
    headers = {'X-CSRFToken': csrftoken,
               'Host': 'www.instagram.com',
               'Origin': 'https://www.instagram.com',
               'Referer': 'https://www.instagram.com/',
               'X-Instagram-AJAX': '1',
               'X-Requested-With': 'XMLHttpRequest',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.120 Chrome/37.0.2062.120 Safari/537.36'}
    session.headers.update(headers)

    login_result = session.post('https://www.instagram.com/accounts/login/ajax/',
                                data=credentials)
    print(login_result)
    main_page_again = session.get('https://www.instagram.com/')
    print(main_page_again)

    import json

    lines = [line for line in main_page_again.content.splitlines()
             if '<script type="text/javascript">window._sharedData = {' in line]
    from ipdb import set_trace; set_trace(context=20)
    unparsed_feed = ''.join(lines)
    start = unparsed_feed.find('{')
    end = unparsed_feed.rfind('}')
    feed = unparsed_feed[start:end+1]
    feed = json.loads(feed)


    print('end')
    return 0


def testweb2():
    api = InstaAPI()
    feed1, next1 = api.user_media_feed()
    feed2, next2 = api.user_media_feed(with_next_url=next1)
    print('first page')
    for entry in feed1:
        print(entry['username'], entry['post_id'])
    print('second page')
    for entry in feed2:
        print(entry['username'], entry['post_id'])
    print('testweb2')


def main():
    args = parse_args()

    # return testweb()
    # return testweb2()

    _log.info('Saving %d (skip %d, fetch %d) of userid %s feed medias to %s',
              args.download, args.skip, args.fetch, args.userid, args.path)
    access_token = open(args.token).read().strip()
    #api = InstagramAPI(access_token=access_token)
    api = InstaAPI()
    saver = InSave(api, args.userid, args.download, args.skip, args.fetch)
    saver.save(args.path)
    saver.show_stats()


if __name__ == '__main__':
    main()
