
# basic algorithm
#   - read config file
#   - get photos (if any) from src (recursively)
#   - read EXIF data and build objects with it
#   - check dst exists else make dst
#   - loop through photos, create dst directories, move (or copy) photos

import EXIF

import os
import shutil
import datetime


# for testing purposes; eventually move to actual config file
TEST_CONFIG = {
    #'src':     '/Users/dgilland/Dropbox/Camera Uploads/',
    #'dst':     '/Users/dgilland/Pictures/Picasa/',
    'src':      'test',
    'dst':      'test-out',
    'saveas':   '{year}/{year}-{month}-{day}/{name}',
}

# datetime tags to use for getting datetime of photo
# NOTE: will try each tag until a valid datetime is extracted
#  once valid will not look at the remaining tags
EXIF_DATETIME_TAGS  = ( 'DateTimeOriginal', 'DateTimeDigitized', 'DateTime' )

# datetime format to attempt to extra from EXIF_DATETIME_TAG
# NOTE: similar to EXIF_DATETIME_TAGS, will attempt to parse datetime using formats listed in order until valid
EXIF_DATETIME_STRF  = ( '%Y:%m:%d %H:%M:%S', )

DATETIME_TUPLE_TAGS    = (
    '%Y %m %d %H %M %S %w %j', ( 'year', 'month', 'day', 'hour', 'minute', 'second', 'weekday', 'yearday' )
)

def read_config( filename ):
    # TODO
    return TEST_CONFIG

class PixifImage:
    def __init__( self, filename, debug=False ):
        self.debug  = debug
        self.file   = open( filename, 'rb' )
        self.exif   = EXIF.process_file( self.file )
        if not self.exif:
            raise Exception( 'no EXIF data' )

        self.filename   = filename
        self.tags       = dict( name=os.path.basename( filename ) )

        self.get_tags()
        self.get_datetime()

    def get_tags( self ):
        tags    = self.exif.keys()
        tags.sort()
        for tag in tags:
            if tag in ('JPEGThumbnail', 'TIFFThumbnail'):
                # skip thumbnails
                continue
            try:
                # format of tag is IFD name followed by tag name, e.g. 'EXIF DateTimeOriginal', 'Image Orientation'
                # drop the IFD name and skip if duplicate
                t = tag.split()[1]
                if t not in self.tags:
                    # use string value for tag value for use with filenames
                    self.tags[t]  = str( self.exif[tag] )
            except Exception:
                # something went wrong but what can we do; tag/tag value not usable
                if self.debug:
                    print 'PixifImage: (warning) could not get tag [%s] for [%s]' % ( tag, self.filename )
                pass

    def get_datetime( self ):
        for t in [ e for e in EXIF_DATETIME_TAGS if e in self.tags ]:
            for strf in EXIF_DATETIME_STRF:
                try:
                    date_str        = str( self.tags[t] )
                    self.datetime   = datetime.datetime.strptime( date_str, strf )
                except ValueError:
                    # invalid date string for format
                    if self.debug:
                        print 'PixifImage: (warning) invalid date string [%s] using format [%s] for [%s]' % ( date_str, strf, self.filename )
                    pass
                except Exception,e:
                    if self.debug:
                        print 'PixifImage: (error) %s for [%s]' % ( e, self.filename )
                    pass

        if self.datetime:
            date_parts   = self.datetime.strftime( DATETIME_TUPLE_TAGS[0] ).split()
            for i,dt_val in enumerate( date_parts ):
                self.tags[ DATETIME_TUPLE_TAGS[1][i] ]   = dt_val

    def as_dict( self ):
        return self.tags

class PixifCollection:
    def __init__( self, src, dst, saveas, debug=False ):
        self.src    = src
        self.dst    = dst
        self.saveas = saveas
        self.debug  = debug
        self.images = None
        self.collect()

    # TODO: may not want to collect files only to re-loop through them in instructions
    # perhaps overload collect() so that it functions as a generator if self.images is None
    def collect( self ):
        # files in source may not all contain EXIF data
        potentials  = get_files( self.src )
        self.images = files_to_pixif( potentials, debug=self.debug )

        return self.images

    def instructions( self ):
        for i in self.images:
            yield ( i, os.path.join( self.dst, self.saveas.format( **i.as_dict() ) ) )

    def copy( self ):
        return self._operate( shutil.copy2 )

    def move( self ):
        return self._operate( shutil.move )

    def _operate( self, operator ):
        # TODO: need to add an overwrite option; currently files are overwritten
        logs  = []
        for image, dst_file in self.instructions():
            try:
                prepare_destination( dst_file )
            except OSError:
                # hopefully issue is that destination root already exists
                pass

            try:
                operator( image.filename, dst_file )
                log = '(success) processed image using %s' % operator
            except OSError,e:
                log = e

        return logs

class PixifLogEntry:
    def __init__( self, text, image, dst ):
        self.error      = error
        self.image      = image
        self.dst        = dst
        self.datetime   = datetime.datetime.today()

def get_files( src ):
    files   = []
    for root, dirs, filenames in os.walk( src ):
        files += [ os.path.join( root, f ) for f in filenames ]
    return files

def files_to_pixif( files, debug=False ):
    pixifs  = []
    for f in files:
        try:
            pixifs.append( PixifImage( f, debug=debug ) )
        except Exception,e:
            if debug:
                print 'files_to_pixif: (error) %s for [%s]' % ( e, f )
            continue
    return pixifs

def prepare_destination( filename ):
    head,tail   = os.path.split( filename )
    os.makedirs( head )

if __name__ == '__main__':

    #photo  = 'test/DSC_1088.jpg'
    #pixif_img  = PixifImage( photo )
    #saveas = os.path.join( TEST_CONFIG['dst'], TEST_CONFIG['saveas'].format( **pixif_img.as_dict() ) )
    #print saveas

    pixif_c = PixifCollection( TEST_CONFIG['src'], TEST_CONFIG['dst'], TEST_CONFIG['saveas'], debug=True )
    #print '\nfiles:'
    #for i in pixif_c.images: print i.filename

    #print '\nimages:'
    #for i in pixif_c.images: print '[%s] move to [%s]' % ( i.filename, os.path.join( TEST_CONFIG['dst'], TEST_CONFIG['saveas'].format( **i.as_dict() ) ) )

    #print '\ndestinations'
    #for d in pixif_c.instructions(): print d
    logs    = pixif_c.move()
    print logs
