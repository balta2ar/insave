from glob import glob


#PATH = '/home/bz/share/dropbox/Dropbox/pics/short/*.jpg'
PATH = '/home/bz/share/dropbox/Dropbox/pics/insave/*.jpg'
SCREEN_WIDTH = 970
SCREEN_HEIGHT = 970
ITEM_WIDTH = 128
SPACE = 2
ITEMS_VERT = SCREEN_HEIGHT / ITEM_WIDTH
ITEMS_HOZT = SCREEN_WIDTH / ITEM_WIDTH
# MAX_ITEMS = 20
PATTERN = '${{image {name} -p {x},{y} -s {width}x{width}}}'


def main():
    cum_width = ITEM_WIDTH + SPACE
    files = sorted(glob(PATH), reverse=True)
    xs = range(0, SCREEN_WIDTH, cum_width)
    ys = range(0, SCREEN_HEIGHT, cum_width)

    max_col = len(xs) - 1
    max_row = len(ys) - 1
    max_items = max_col * max_row
    # max_items = 1
    # print(max_items, len(files))

    for i, filename in enumerate(files[:max_items]):
        col = i / ITEMS_VERT
        row = i % ITEMS_VERT

        x, y = xs[col], ys[row]
        print(PATTERN.format(name=filename, x=x, y=y, width=ITEM_WIDTH))


if __name__ == '__main__':
    main()
