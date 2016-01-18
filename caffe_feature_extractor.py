import numpy as np
import os
import sys
import getopt
from glob import glob


# Main path to your caffe installation
caffe_root = '/opt/caffe/'

# Model prototxt file
model_prototxt = caffe_root + 'models/bvlc_googlenet/deploy.prototxt'

# Model caffemodel file
model_trained = caffe_root + 'models/bvlc_googlenet/bvlc_googlenet.caffemodel'

# File containing the class labels
imagenet_labels = caffe_root + 'data/ilsvrc12/synset_words.txt'

# Path to the mean image (used for input processing)
mean_path = caffe_root + 'python/caffe/imagenet/ilsvrc_2012_mean.npy'

# Name of the layer we want to extract
layer_name = 'pool5/7x7_s1'

sys.path.insert(0, caffe_root + 'python')
import caffe


def get_imagenet_features(names):
    caffe.set_mode_gpu()

    net = caffe.Classifier(model_prototxt, model_trained,
                           mean=np.load(mean_path).mean(1).mean(1),
                           channel_swap=(2,1,0),
                           raw_scale=255,
                           image_dims=(256, 256))

    features = []
    for name in names:
        input_image = caffe.io.load_image(name.strip())
        net.predict([input_image], oversample=False)
        #feature = net.blobs[layer_name].data[0].reshape(1,-1)
        feature = net.blobs[layer_name].data[0].reshape(-1).copy()
        features.append(feature)
    return features


def main(argv):
    inputfile = ''
    outputfile = ''

    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print 'caffe_feature_extractor.py -i <inputfile> -o <outputfile>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print 'caffe_feature_extractor.py -i <inputfile> -o <outputfile>'
            sys.exit()
        elif opt in ("-i"):
            inputfile = arg
        elif opt in ("-o"):
            outputfile = arg

    print 'Reading images from "', inputfile
    print 'Writing vectors to "', outputfile

    # Setting this to CPU, but feel free to use GPU if you have CUDA installed
    #caffe.set_mode_cpu()
    caffe.set_mode_gpu()
    # Loading the Caffe model, setting preprocessing parameters
    net = caffe.Classifier(model_prototxt, model_trained,
                           mean=np.load(mean_path).mean(1).mean(1),
                           channel_swap=(2,1,0),
                           raw_scale=255,
                           image_dims=(256, 256))

    # Loading class labels
    with open(imagenet_labels) as f:
        labels = f.readlines()

    # This prints information about the network layers (names and sizes)
    # You can uncomment this, to have a look inside the network and choose which layer to print
    #print [(k, v.data.shape) for k, v in net.blobs.items()]
    #exit()

    # Processing one image at a time, printint predictions and writing the vector to a file
    with open(inputfile, 'r') as reader:
        with open(outputfile, 'w') as writer:
            writer.truncate()
            for image_path in reader:
                image_path = image_path.strip()
                input_image = caffe.io.load_image(image_path)
                prediction = net.predict([input_image], oversample=False)
                print os.path.basename(image_path), ' : ', labels[prediction[0].argmax()].strip(), ' (', prediction[0][prediction[0].argmax()], ')'
                #feature = net.blobs[layer_name].data[0].reshape(-1)
                feature = net.blobs[layer_name].data[0].reshape(1,-1)
                #print(feature)
                np.savetxt(writer, feature, fmt='%.8g')


def test():
    names = glob('./data/**/*.jpg')[:3]
    features = get_imagenet_features(names)
    print(names)
    for x in features:
        print(x)
    print(len(features))


if __name__ == "__main__":
    #test()
    main(sys.argv[1:])
