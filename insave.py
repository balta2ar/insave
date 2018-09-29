import os
import re
import json
import logging
import requests
import argparse
from pprint import pformat
from netrc import netrc
from datetime import datetime
from os.path import join as J
from urllib import quote_plus
# from instagram.client import InstagramAPI

from bs4 import BeautifulSoup


LOGLEVEL = logging.INFO
# LOGLEVEL = logging.DEBUG
FORMAT = '%(asctime)s %(process)s %(name)s %(levelname)-8s - %(message)s'
_log = logging.getLogger('insave')
COOKIES_FILENAME = 'cookies.json'


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


def spit(data, filename, mode='w'):
    with open(filename, mode) as file_:
        file_.write(data)


def spit_json(data, filename, mode='w'):
    spit(json.dumps(data, indent=4), filename, mode)


def slurp(filename):
    with open(filename) as file_:
        return file_.read()


def save_cookies(session, filename):
    #cookies = requests.utils.dict_from_cookiejar(self._session.cookies)
    cookies = session.cookies.get_dict()
    _log.debug('cookies %s', cookies)
    spit_json(cookies, filename)


def load_cookies(filename):
    try:
        return json.loads(slurp(filename))
    except:
        return {}


class InstaAPI(object):
    SHARED_DATA_SUBSTRING = '<script type="text/javascript">window._sharedData = {'
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'

    def __init__(self):
        self._logged_in = False
        self._query_hash = None
        self._session = requests.Session()
        self._set_user_agent()
        self._session.cookies.update(load_cookies(COOKIES_FILENAME))

    def _set_user_agent(self):
        headers = {'User-Agent': self.USER_AGENT}
        self._session.headers.update(headers)

    def _update_headers(self, csrftoken):
        self._set_user_agent()
        headers = {
            'X-CSRFToken': csrftoken,
            'Host': 'www.instagram.com',
            'Origin': 'https://www.instagram.com',
            'Referer': 'https://www.instagram.com/',
            'X-Instagram-AJAX': '1',
            'X-Requested-With': 'XMLHttpRequest',
        }
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
        main_page_again = self._session.get('https://www.instagram.com/')

        if not InstaAPI.SHARED_DATA_SUBSTRING in main_page_again.content:
            _log.error('No line with sharedData in main page response (login)')
            _log.error(main_page_again.content)
            return False

        _log.debug('Logged in')
        save_cookies(self._session, 'cookies.json')

        self._query_hash = self._find_query_hash(main_page_again.text)

        return True

    def _find_query_hash(self, main_page):
        soup = BeautifulSoup(main_page, 'html.parser')
        scripts = soup.find_all('script')
        scripts = [script for script in scripts
                   if '/static/bundles/base/ConsumerCommons.js'
                   in script.attrs.get('src', '')]

        if len(scripts) != 1:
            raise ValueError('Expected to find only one script, '
                             'found this many: %s: %s' %
                             (len(scripts), scripts))

        # 's' is one of three hashes that seems to contain lookup hash for page
        # feed
        script_url = 'https://www.instagram.com%s' % scripts[0].attrs['src']
        body = self._session.get(script_url).text
        query_hash = self._find_hashes(body)['s']
        return query_hash

    def _find_hashes(self, text):
        """
        Example results:

        ['s="c409f8bda63382c86db99f2a2ea4a9b2"',
         'l="60b755363b5c230111347a7a4e242001"',
         'd="ae21d996d1918b725a934c0ed7f59a74"']

        Returns a dict where key={s,l,d}, value=hash
        """
        substring = '="/graphql/query/";var'
        index = text.index(substring)
        if index == -1:
            raise ValueError('"%s" substring not found' % substring)

        text = text[index:index+200]
        hashes = re.findall(r'[a-z]="[a-z0-9]{32}"', text)
        if len(hashes) != 3:
            raise ValueError('Expected to find 3 hashes, found: %s: %s' %
                             (len(hashes), hashes))

        result = {}
        for key, value in [h.split('=') for h in hashes]:
            result[key] = value.strip('"')
        return result

    def _find_preload_query(self, text):
        """
        Since ~24.02.2018 initial graphql request was put into <link preload>
        section of the first HTML page.
        """
        results = re.findall(r'"/graphql/query/[^"]*"', text)
        results = [s.strip('"') for s in results if 'only_stories' not in s]
        if not results:
            return None
        return results[0]

    def _graphql_query(self, cursor=None):
        """
        https://www.instagram.com/graphql/query/?query_hash=c409f8bda63382c86db99f2a2ea4a9b2&
            variables={"fetch_media_item_count":12,
                    "fetch_media_item_cursor":"KK8BARAAAAI4ACAAGAAQAAgACAAIAP_3_____u___f-_____v__9v3_-__3f__3u___f___f_7_f__-__f_7________7_-vv_-_3__-___77____989405s87H_llVJ63i5k_h-Pv3_3_3__fvfa6___bS__ff77ff____f_2___f9__9_9_______vfv__f_533v__f_b_v_3_3_-7_7_-__-_6NzpfjzwsDrxvwJgABburdLUxFkA",
                    "fetch_comment_count":4,
                    "fetch_like":10,
                    "has_stories":false}
        """
        variables = {}
        if cursor is not None:
            variables={"fetch_media_item_count": 12,
                       "fetch_media_item_cursor": cursor,
                       "fetch_comment_count": 4,
                       "fetch_like": 10,
                       "has_stories": False}
        variables = quote_plus(json.dumps(variables))
        url = ('https://www.instagram.com/graphql/query/?'
               'query_hash=%s&variables=%s' % (self._query_hash, variables))
        _log.debug('graphql url: %s', url)
        reply = self._session.get(url)
        return reply


    def _get_first_page(self):
        main_page = self._session.get('https://www.instagram.com/')
        csrftoken = main_page.cookies['csrftoken']
        self._update_headers(csrftoken)
        spit(main_page.content, 'main.html')

        reply = self._graphql_query()

        # if not InstaAPI.SHARED_DATA_SUBSTRING in main_page.content:
        #     _log.error(
        #         'No line with sharedData in main page response (first page)')
        #     _log.error(main_page.content)
        #     return None
        #
        # lines = [line for line in main_page.content.splitlines()
        #          if InstaAPI.SHARED_DATA_SUBSTRING in line]
        #
        # unparsed_feed = ''.join(lines)
        # start = unparsed_feed.find('{')
        # end = unparsed_feed.rfind('}')
        # if (start == -1) or (end == -1):
        #     _log.error('Could not find start or end of JSON in sharedData (first page)')
        #     _log.error(unparsed_feed)
        #     return None

        # preload_query = self._find_preload_query(main_page.content)
        # if preload_query is None:
        #     _log.error(
        #         '<link rel="preload" graphql queries were not found, check main-page.html')
        #     _log.error(main_page.content)
        #     return None

        # feed = unparsed_feed[start:end+1]

        # preload_page = self._session.get(
        #     'https://www.instagram.com%s' % preload_query)
        # feed = preload_page.content

        try:
            #feed = json.loads(feed)
            feed = reply.json()
            spit_json(feed, 'feed-first-page.json')
        except Exception as e:
            _log.error('Could not load JSON response (first page)')
            _log.error(feed)
            return None

        try:
            #feed_page = feed['entry_data']['FeedPage'][0]
            return self._simplify_feed(
                feed['data'], 'feed-first.json')
                #feed_page['graphql'], 'feed-first.json')
                # feed['data'], 'feed-first.json')
        except KeyError as e:
            _log.error('Could not get first page: %s', e)
            _log.error('Feed: %s', pformat(feed))

    def _get_next_page(self, end_cursor):
        reply = self._graphql_query(end_cursor)

        try:
            feed = reply.json()
        except Exception as e:
            _log.error('Cannot decode JSON for the next page')
            _log.error(e)
            _log.error(next_page.content)
            _log.error(next_page.status)
            _log.error(next_page.reason)
            raise
        return self._simplify_feed(feed['data'], 'feed-second.json')

    # def _get_next_page(self, end_cursor):
    #     next_page = self._session.get(
    #         'https://www.instagram.com/graphql/query/'
    #         '?query_id=17882195038051799'
    #         '&fetch_media_item_count=12'
    #         '&fetch_media_item_cursor={cursor}'
    #         '&fetch_comment_count=4&'
    #         'fetch_like=10'.format(cursor=end_cursor))
    #
    #     try:
    #         feed = json.loads(next_page.content)
    #     except Exception as e:
    #         _log.error('Cannot decode JSON for the next page')
    #         _log.error(e)
    #         _log.error(next_page.content)
    #         _log.error(next_page.status)
    #         _log.error(next_page.reason)
    #         raise
    #     return self._simplify_feed(feed['data'], 'feed-second.json')

    # def _simplify_feed(self, feed, filename):
    #     spit_json(feed, filename)
    #     media = feed['user']['edge_web_feed_timeline']
    #     end_cursor = media['page_info']['end_cursor']
    #
    #     simple = []
    #     for node in media['edges']:
    #         node = node['node']
    #         entry = {
    #             'username': node['owner']['username'],
    #             'username_id': node['owner']['id'],
    #             'date': node['taken_at_timestamp'],
    #             'is_video': node['is_video'],
    #             'post_id': node['id'],
    #             'url': node['display_url'],
    #         }
    #         simple.append(entry)
    #
    #     return simple, end_cursor

    def _simplify_feed(self, feed, filename):
        spit_json(feed, filename)
        media = feed['user']['edge_web_feed_timeline']
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

        # return '{0}-{1}-{2}.jpg'.format(media.created_time.isoformat(),
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
        spit(r.content, name, 'wb')
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
                # if media.type != 'image':
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
    parser.add_argument('-p', '--path', default='media',
                        help='path to saved media')
    parser.add_argument('-u', '--userid', default='46764821',
                        help='user id (not name)')
    parser.add_argument('-d', '--download', default=100, type=int,
                        help='number of recent medias to download before termination')
    parser.add_argument('-s', '--skip', default=100, type=int,
                        help='number of recent medias to skip CONTINUOUSLY before termination')
    parser.add_argument('-f', '--fetch', default=100, type=int,
                        help='number of medias to ask in each API request')
    parser.add_argument('-q', '--quiet', action='store_true',
                        default=False, help='do not print to stdout')
    parser.add_argument('-l', '--log', default=None, help='log to file')
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
    # enable_requests_debug()

    # return testweb()
    # return testweb2()

    _log.info('Saving %d (skip %d, fetch %d) of userid %s feed medias to %s',
              args.download, args.skip, args.fetch, args.userid, args.path)
    #access_token = open(args.token).read().strip()
    #api = InstagramAPI(access_token=access_token)
    api = InstaAPI()
    saver = InSave(api, args.userid, args.download, args.skip, args.fetch)
    saver.save(args.path)
    saver.show_stats()


if __name__ == '__main__':
    main()
