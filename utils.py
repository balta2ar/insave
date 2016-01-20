from collections import namedtuple


PostInfo = namedtuple('PostInfo', 'timestamp username postid userid')


def encode_int(value, base):
    """Convert int value to a list of values in another base"""
    encoded = []
    while value > 0:
        encoded.append(value % base)
        value /= base
    encoded.reverse()
    return encoded


def post_id_to_short_url(post_id):
    encoded = encode_int(post_id, 64)
    return ''.join(map(URL_CHARACTERS.__getitem__, encoded))


def post_id_to_full_url(post_id):
    encoded = encode_int(post_id, 64)
    short = ''.join(map(URL_CHARACTERS.__getitem__, encoded))
    return 'https://www.instagram.com/p/{0}'.format(short)


def post_id_to_thumbnail_url(post_id):
    full = post_id_to_full_url(post_id)
    return '{0}/media/?size=t'.format(full)


def parse_filename(filename):
    # Sample filename
    # '2016-01-18T07:16:28-sol_blackhands-1165021344299433317_2010758534.jpg'
    # Cut timestamp from the beginning
    timestamp, rest = filename[:19], filename[20:]
    # Cut off extension and split
    username, postid_userid = rest[:-4].split('-')
    userid, postid = postid_userid.split('_')
    return PostInfo(timestamp, username, userid, postid)


TABLE = {
    "0": "A",
    "1": "B",
    "2": "C",
    "3": "D",
    "4": "E",
    "5": "F",
    "6": "G",
    "7": "H",
    "8": "I",
    "9": "J",
    "a": "K",
    "b": "L",
    "c": "M",
    "d": "N",
    "e": "O",
    "f": "P",
    "g": "Q",
    "h": "R",
    "i": "S",
    "j": "T",
    "k": "U",
    "l": "V",
    "m": "W",
    "n": "X",
    "o": "Y",
    "p": "Z",
    "q": "a",
    "r": "b",
    "s": "c",
    "t": "d",
    "u": "e",
    "v": "f",
    "w": "g",
    "x": "h",
    "y": "i",
    "z": "j",
    "A": "k",
    "B": "l",
    "C": "m",
    "D": "n",
    "E": "o",
    "F": "p",
    "G": "q",
    "H": "r",
    "I": "s",
    "J": "t",
    "K": "u",
    "L": "v",
    "M": "w",
    "N": "x",
    "O": "y",
    "P": "z",
    "Q": "0",
    "R": "1",
    "S": "2",
    "T": "3",
    "U": "4",
    "V": "5",
    "W": "6",
    "X": "7",
    "Y": "8",
    "Z": "9",
    "$": "-",
    "_": "_"
}

URL_CHARACTERS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
    "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d",
    "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s",
    "t", "u", "v", "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7",
    "8", "9", "-", "_"
]
