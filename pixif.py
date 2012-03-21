# Pixif: Picture Transfer <https://github.com/dgilland/pixif>
# Author: Derrick Gilland <https://github.com/dgilland>
# License: Unlicense <http://unlicense.org/>
# Version: 0.1

import EXIF

import os
import shutil
import datetime
import ConfigParser

# datetime tags to use for getting datetime of photo
# NOTE: will try each tag until a valid datetime is extracted
#  once valid will not look at the remaining tags
EXIF_DATETIME_TAGS  = ( 'DateTimeOriginal', 'DateTimeDigitized', 'DateTime' )

# datetime format to attempt to extra from EXIF_DATETIME_TAG
# NOTE: similar to EXIF_DATETIME_TAGS, will attempt to parse datetime using formats listed in order until valid
EXIF_DATETIME_STRF  = ( '%Y:%m:%d %H:%M:%S', )

DATETIME_TUPLE_TAGS    = (
    '%Y %m %d %H %M %S %w %j', ( 'Year', 'Month', 'Day', 'Hour', 'Minute', 'Second', 'Weekday', 'Yearday' )
)

class PixifImage:
    def __init__( self, filename, debug=False ):
        self.debug  = debug
        self.file   = open( filename, 'rb' )
        self.exif   = EXIF.process_file( self.file )
        if not self.exif:
            raise Exception( 'no EXIF data' )

        self.filename   = filename
        self.tags       = {
            'Name':         os.path.basename( filename ),
            'Extension':    os.path.splitext( filename )[1]
        }

        self.get_tags()
        self.get_datetime()
        self.file.close()

    def __repr__( self ):
        return '<PixifImage at %s>' % ( self.filename )

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
                # something went wrong but what can we do; tag value not usable
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
    def __init__( self, src, dst, saveas, overwrite=True, logger=None, debug=False ):
        self.src    = src
        self.dst    = dst
        self.saveas = saveas
        self.overwrite  = overwrite
        self.logger = logger
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
        for image, dst_file in self.instructions():
            if self.overwrite or not os.path.exists( dst_file ):
                try:
                    prepare_destination( dst_file )
                except OSError:
                    # destination root already exists
                    pass

                log = ''
                try:
                    operator( image.filename, dst_file )
                    log = '(success) processed image using %s' % operator
                except OSError,e:
                    log = e
            else:
                log = '(warning) could not process image because file already exists'

            if log:
                self.logger.append( log, image, dst_file )

class PixifLogger:
    def __init__( self, section, filename_out ):
        self.section        = section
        self.filename_out   = filename_out
        self.clear()

    def append( self, text, image, dst ):
        self.logs.append( PixifLogEntry( text, image, dst, self.section ) )

    def clear( self ):
        self.logs   = []

    def write( self, filename_out=None ):
        if self.logs:
            f_out   = filename_out if filename_out else self.filename_out
            try:
                f_out   = open( f_out, 'ab' )
            except IOError:
                pass
            else:
                for l in self.logs:
                    try:
                        f_out.write( str(l) + '\n' )
                    except IOError:
                        pass

                f_out.close()

class PixifLogEntry:
    def __init__( self, text, image, dst, section ):
        self.text       = text
        self.image      = image
        self.dst        = dst
        self.section    = section
        self.datetime   = datetime.datetime.today()

    def __repr__( self ):
        return '\t'.join( [ self.datetime.isoformat(' '), self.section, self.text, self.image.filename, self.dst ] )

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


def read_config_file( filename, booleans ):
    config  = ConfigParser.RawConfigParser()
    config.read( filename )

    config_dict = dict()
    for s in config.sections():
        config_dict[s]  = dict()

        for name,_ in config.items(s):
            if config.has_option( s, name ):
                if name in booleans:
                    value   = config.getboolean( s, name )
                else:
                    value   = config.get( s, name )

            config_dict[s][name]    = value

    return config_dict

def read_config_opts( opts, booleans ):
    config  = dict( section=dict() )
    for o,opt in opts.iteritems():
        new_key = o.replace( '--', '' )

        if new_key in booleans:
            config['section'][new_key] = True
        else:
            config['section'][new_key] = opt

    return config

def config_merge_defaults( config ):
    defaults    = {
        'method':       'copy',
        'log':          False,
        'overwrite':    False,
        'enabled':      True
    }

    for c in config:
        config[c]   = dict( defaults.items() + config[c].items() )

if __name__ == '__main__':

    import sys
    import getopt

    try:
        opts, args  = getopt.getopt( sys.argv[1:], 's:d:a:m:lo', [ 'src=', 'dst=', 'saveas=', 'method=', 'log', 'overwrite' ] )
        booleans    = [ 'log', 'overwrite', 'enabled' ]

        if args:
            config_file = args[0]
            config  = read_config_file( config_file, booleans )
        else:
            config_file = ''
            opt_map = {
                '-s':   'src',
                '-d':   'dst',
                '-a':   'saveas',
                '-m':   'method',
                '-l':   'log',
                '-o':   'overwrite',
            }

            opts_dict   = dict( opts )
            opts        = dict()
            for o,opt in opts_dict.iteritems():
                if o in opt_map:
                    opts[ opt_map[o] ]  = opt

            config  = read_config_opts( opts, booleans )

        config_merge_defaults( config )

        required    = set( [ 'src', 'dst', 'saveas', 'method' ] )
        opts_valid  = True
        for c,conf in config.iteritems():
            if len( required - set(conf.keys()) ) > 0:
                opts_valid  = False
                break

        if not opts_valid:
            print 'error:', 'missing required options'
            sys.exit()

    except getopt.GetoptError:
        print 'error:', 'incorrect usage'
    else:
        logger_dir,_    = os.path.split( config_file )
        logger_file     = os.path.join( logger_dir, 'pixif.log' )

        for c,cfg in config.iteritems():
            if not cfg['enabled']:
                continue

            logger  = PixifLogger( c, logger_file )

            try:
                pixif_c = PixifCollection( cfg['src'], cfg['dst'], cfg['saveas'], cfg['overwrite'], logger=logger )

                if cfg['method'] == 'copy':
                    pixif_c.copy()
                elif cfg['method'] == 'move':
                    pixif_c.move()

            except Exception,e:
                print 'error:', e

            logger.write()
            logger.clear()

    sys.exit()

