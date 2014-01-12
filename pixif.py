# Pixif: Picture Transfer <https://github.com/dgilland/pixif>
# Author: Derrick Gilland <https://github.com/dgilland>
# License: Unlicense <http://unlicense.org/>
# Version: 0.1

import EXIF

import os
import shutil
from datetime import datetime
import ConfigParser

class PixifLogger(object):
    def __init__(self, section, filename_out):
        self.section = section
        self.filename_out = filename_out
        self.clear()

    def append(self, text, image, dst):
        self.logs.append('\t'.join([
            datetime.today().isoformat(),
            self.section,
            text,
            image.filename,
            dst
        ]))

    def clear(self):
        self.logs = []

    def write(self, filename_out=None):
        if not self.logs:
            return

        f_out = filename_out if filename_out else self.filename_out

        try:
            with open(f_out, 'a') as f:
                for log in self.logs:
                    try:
                        f.write(str(log) + '\n')
                    except IOError:
                        pass
        except IOError:
            pass

class PixifImage(object):
    # Datetime tags to use for getting datetime of photo.
    # Will try each tag until a valid datetime is extracted once valid will not look at the remaining tags.
    EXIF_DATETIME_TAGS = ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime')

    # Datetime format to attempt to extra from EXIF_DATETIME_TAG.
    # Similar to EXIF_DATETIME_TAGS, will attempt to parse datetime using formats listed in order until valid.
    EXIF_DATETIME_STRF = ('%Y:%m:%d %H:%M:%S',)

    DATETIME_FORMAT = {
        'tags': ('Year', 'Month', 'Day', 'Hour', 'Minute', 'Second', 'Weekday', 'Yearday'),
        'strf': ('%Y',   '%m',    '%d',  '%H',   '%M',     '%S',     '%w',      '%j')
    }

    def __init__(self, filename):
        self.filename = filename
        self.datetime = None
        self.tags = {}

        with open(filename, 'rb') as f:
            self.exif_data = EXIF.process_file(f)

        self.set_file_tags()
        self.set_exif_tags()
        self.set_datetime_tags()

    def __repr__(self):
        return '<PixifImage at {0}>'.format(self.filename)

    def __iter__(self):
        return self.tags.iteritems()

    def set_file_tags(self):
        self.tags.update({
            'Name': os.path.basename(self.filename),
            'Extension': os.path.splitext(self.filename)[1]
        })

    def set_exif_tags(self):
        for tag in sorted(self.exif_data.keys()):
            # skip thumbnails
            if 'thumbnail' in tag.lower():
                continue

            try:
                # format of tag is IFD name followed by tag name, e.g. 'EXIF DateTimeOriginal', 'Image Orientation'
                # drop the IFD name and skip if duplicate
                t = tag.split()[1]

                # use string value for tag value for use with filenames
                self.tags.setdefault(t, str(self.exif_data[tag]))
            except Exception:
                # something went wrong but what can we do; tag value not usable
                pass

    def set_datetime_tags(self):
        self.set_datetime()

        if self.datetime:
            date_parts = self.datetime.strftime(' '.join(self.DATETIME_FORMAT['strf'])).split()
            for i, value in enumerate(date_parts):
                tag = self.DATETIME_FORMAT['tags'][i]
                self.tags[tag] = value

    def set_datetime(self):
        if self.exif_data:
            self.datetime = self.datetime_from_exif()

        if not self.exif_data or not self.datetime:
            self.datetime = self.datetime_from_file()

    def datetime_from_exif(self):
        dt = None

        for tag in self.EXIF_DATETIME_TAGS:
            if tag not in self.tags:
                continue

            for strf in self.EXIF_DATETIME_STRF:
                try:
                    date_str = str(self.tags[tag])
                    dt = datetime.strptime(date_str, strf)
                    break
                except Exception:
                    pass

        return dt

    def datetime_from_file(self):
        return datetime.fromtimestamp(os.path.getmtime(self.filename))


class PixifCollection(object):
    VALID_FILE_EXT = ('.jpg', '.jpeg', '.png')

    def __init__(self, src, dst, saveas, method='move', overwrite=False, logger=None, **ignore):
        self.src = src
        self.dst = dst
        self.saveas = saveas
        self.method = method
        self.overwrite = overwrite
        self.logger = logger

        self.set_images()

    def execute(self):
        if self.method == 'copy':
            self.copy()
        elif self.method == 'move':
            self.move()

    def copy(self):
        return self._process(shutil.copy2)

    def move(self):
        return self._process(shutil.move)

    def _process(self, operator):
        for image in self.images:
            log = None
            dst_file = os.path.join(self.dst, self.saveas.format(**dict(image)))

            if self.overwrite or not os.path.exists(dst_file):
                head, tail = os.path.split(dst_file)

                try:
                    os.makedirs(head)
                except OSError:
                    # destination root already exists
                    pass

                try:
                    operator(image.filename, dst_file)
                    log = '(success) processed image using {0}'.format(operator)
                except OSError as e:
                    log = str(e)
            else:
                log = '(warning) could not process image because file already exists'

            if log and self.logger:
                self.logger.append(log, image, dst_file)

    def set_images(self):
        self.images = []

        for root, dirs, filenames in os.walk(self.src):
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in self.VALID_FILE_EXT:
                    try:
                        self.images.append(PixifImage(os.path.join(root, filename)))
                    except Exception as e:
                        print e

class PixifConfig(dict):
    opts_map = {
        '-s': 'src',
        '-d': 'dst',
        '-a': 'saveas',
        '-m': 'method',
        '-l': 'log',
        '-o': 'overwrite',
    }

    flags = ['log', 'overwrite', 'enabled']

    defaults = {
        'method': 'copy',
        'log': False,
        'overwrite': False,
        'enabled': True
    }

    def __init__(self, filename=None, opts=None):
        self.filename = filename
        self.opts = opts

        if filename:
            # Assume that first element is config file name.
            self.from_file(filename)
        elif opts:
            self.from_opts(opts)

    def from_file(self, filename):
        self.clear()

        config = ConfigParser.RawConfigParser()
        config.read(filename)

        for s in config.sections():
            self[s] = self.defaults.copy()

            for name,_ in config.items(s):
                if config.has_option(s, name):
                    if name in self.flags:
                        value = config.getboolean(s, name)
                    else:
                        value = config.get(s, name)

                self[s][name] = value

    def from_opts(opts):
        self['section'] = self.defaults.copy()

        opts_dict = dict(opts)

        for o, opt in opts_dict.iteritems():
            if o in self.opts_map:
                key = self.opts_map[o]
            else:
                key = o.replace('--', '')

            self['section'][key] = True if key in self.flags else opt

def main(config_filename, opts):
    config = PixifConfig(filename=config_filename, opts=opts)
    logger_file = os.path.join(os.path.split(config_filename)[0], 'pixif.log')

    for c, cfg in config.iteritems():
        if not cfg['enabled']:
            continue

        logger = PixifLogger(c, logger_file)

        collection = PixifCollection(logger=logger, **cfg)
        collection.execute()

        logger.write()

if __name__ == '__main__':

    import sys
    import getopt

    try:
        opts, unparsed = getopt.getopt(
            sys.argv[1:],
            's:d:a:m:lo',
            ['src=', 'dst=', 'saveas=', 'method=', 'log', 'overwrite']
        )
    except getopt.GetoptError:
        print 'ERROR: Incorrect usage'
    else:
        config_filename = unparsed[0] if unparsed else ''
        main(config_filename, opts)

