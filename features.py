#import gzip
#from glob import glob
import numpy as np
from scipy import misc
import pywt
from string import strip

from os.path import basename

from bottle import route
from bottle import run
from bottle import request
from bottle import static_file

#from caffe_feature_extractor import get_imagenet_features as _get_imagenet_features

import logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S',
                    level=logging.DEBUG)


def extract(names, output_filename, feature_type):
    #names = glob(basedir + '/**/*.jpg') + glob(basedir + '/*.jpg')
    extractor = {
        'haar': _get_haar_features,
        #'imagenet': _get_imagenet_features
    }[feature_type]
    # print(names)
    features = extractor(names)
    return features


def knn(X):
    #num_test = X.shape[0]
    #num_train = self.X_train.shape[0]
    #dists = np.zeros((num_test, num_train))
    inner = X.dot(X.T)
    #Xte = np.square(X).sum(axis=1)
    #Xtr = np.square(X).sum(axis=1)
    XS = np.square(X).sum(axis=1)
    #dists = np.sqrt(-2*inner + XS + np.matrix(XS, dtype=np.float32).T)
    dists = np.sqrt(-2*inner + XS + XS)
    return dists


def similar(dists, i, n):
    neighbors = np.argsort(dists[i])[1:n+1]
    return neighbors


#def save():
#    with gzip.open(output_filename, 'w') as file_object:
#        for name, feature in zip(names, features):
#            file_object.write('{0}\t{1}\n'.format(name, list(feature)))


def _get_haar_features(names):
    return map(_get_haar_feature, names)


def _get_haar_feature(filename):
    data = misc.imread(filename)
    data = misc.imresize(data, (64, 64))
    #data.resize(64, 64)

    feature_layers = np.zeros((32, 32, 3), dtype=np.float32)
    additional = np.empty(4)

    for index in range(3):
        layer = data[:, :, index]
        layer = np.float32(layer)
        additional[index] = layer.mean()
        #layer /= 255.0
        #print(layer.min(), layer.max(), layer.mean())
        #print(layer[:1])

        haar = pywt.wavedec2(data=layer, wavelet='haar', level=1)
        cA = haar[0]
        feature_layers[:, :, index] = cA

    height, width, _ = data.shape
    aspect = float(width)/(width+height)
    additional[-1] = aspect
    features = np.concatenate((feature_layers.reshape(32*32*3), additional))
    return features


SIMILAR_HTML = """
<html>
<body>
{original}
<br>
<hr>
{similar}
</body>
</html>
"""


IMAGE_ROOT = '/mnt/big_ntfs/doc/pic/dropbox/insave/2016-01/'


def img(id):
    href = '/similar/{0}'.format(id)
    return '''
<a href="{href}">
    <img src="/image/{src}" width="128" height="128">
</a>'''.format(href=href, src=basename(names[id]))


@route('/similar/<id>')
def http_similar(id):
    id = int(id)
    neighbors = similar(dists, id, 10)
    img_original = img(id)
    img_similar = ''.join(map(img, neighbors))
    return SIMILAR_HTML.format(original=img_original,
                               similar=img_similar)

    #return 'Hello there, %s' % id


@route('/image/<filename>')
def http_image(filename):
    return static_file(filename, root=IMAGE_ROOT, mimetype='image/jpeg')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--filelist", type=str, help="Input list of file names")
    parser.add_argument("--output", type=str, help="Output filename")
    parser.add_argument("--extractor", type=str, help="Feature extractor")
    parser.add_argument("--id", type=int, help="Requested image id")
    parser.add_argument("-n", type=int, help="Number of similar items")
    args = parser.parse_args()

    #logging.info('Reading file %s', args.output)
    names = map(strip, open(args.filelist).readlines())
    dists = np.load(args.output)

    run(host='0.0.0.0', port=8030, debug=True)

    # logging.info('Requested %d items for image %d', args.n, args.id)
    # neighbors = similar(dists, args.id, args.n)
    #
    # logging.info('Neighbors %s', neighbors)
    # logging.info('Original %s', names[args.id])
    # for i, neighbor in enumerate(neighbors):
    #     logging.info('Neighbor %d %s', i, names[neighbor])
    #
    # exit(0)
    #
    # logging.info('args: %s', args)
    #
    # # Read file names
    # logging.info('Reading filenames from %s', args.filelist)
    # names = map(strip, open(args.filelist).readlines())
    # logging.info('%s input files', str(len(names)))
    #
    # # Extract features
    # logging.info('Extracting features')
    # extractor = {
    #     'haar': _get_haar_features,
    #     #'imagenet': _get_imagenet_features
    # }[args.extractor]
    # features = extractor(names)
    #
    # # Compute KNearestNeighbor
    # logging.info('Computing KNN')
    # dists = knn(np.array(features, dtype=np.float32))
    # print('dists', dists.dtype)
    #
    # # Save result
    # logging.info('Saving dists to %s', args.output)
    # np.save(args.output, dists)
