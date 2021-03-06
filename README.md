# pixif

## Description

Pixif can copy or move photos from a source directory to a destination directory using EXIF data to build the resulting file path.

For example, photos saved in `Dropbox/Camera Uploads/` can automatically be moved to `Pictures/2012/2012-01-02/20120102-IMG001.jpg` which would be based on the date the photo was taken.

Pixif was mainly developed to easily transfer photos uploaded via Dropbox's `Camera Upload` feature to a main photo storage folder located elsewhere.

## Author

Derrick Gilland

<https://github.com/dgilland>

## Requirements

- Python 2.6+

# Acknowledgments

Special thanks to [ianare](http://ianare.users.sourceforge.net) for developing [EXIF](http://sourceforge.net/projects/exif-py), the EXIF python module used in this project.

# License

See LICENSE file.

# Documentation

## Usage

Pixif can be run from the command-line using 2 methods:

1. Command-line options
2. Configuration file

## Command-Line Options

Full invocation using short options:

    $ python pixif.py -s /path/to/source -d /path/to/destination -a {EXIF}/{Tag}/{Save}-{Structure} -m method -l -o

Full invocation using long options:

    $ python pixif.py --src /path/to/source --dst /path/to/destination --saveas {EXIF}/{Tag}/{Save}-{Structure} --method method --log --overwrite

## Options

### -s, --src [required]

String. Source file path.

### -d, --dst [required]

String. Destination file path.

### -a, --saveas [required]

String. Format string syntax with EXIF tag names delimited by braces `{}`, e.g., `{Year}/{Year}-{Month}-{Day}/{Name}`.

*See EXIF.py's EXIF_TAGS constant for full list.*

### -m, --method [optional, default: copy]

String. Acceptable values: `copy` or `move`.

### -l, --log [optional, default: False]

Boolean. Enable logging.

### -o, --overwrite [optional, default: False]

Boolean. Overwrite existing photos when transferred.

## Configuration File Structure

_See sample-config.ini._

    ; section titles names are arbitrary but will be used as id for log entries
    [alpha]

    ; src: source folder location
    src=test/in

    ; dst: destination folder location
    dst=test/out

    ; saveas: format for saving file
    saveas={Year}/{Year}-{Month}-{Day}/{Name}
    ; given the above with
    ;   src photo: test/in/IMG_001.jpg taken 2012/01/02
    ; resultant save file will be:
    ;   dst photo: test/out/2012/2012-01-02/IMG_001.jpg

    ; method: copy or move files
    method=copy

    ; log: true/false indicates whether to log to pixif.log in same folder as this config
    log=true

    ; overwrite: true/false indicates whether to overwrite existing files in destination
    overwrite=true

    ; enabled: true/false enables/disables this section
    enabled=true

## Scheduled Transfers Using Cron

Below is an example setup for using Cron to schedule periodic photo transfers.

### Configuration File

**/Users/username/Dropbox/Camera Uploads/pixif.ini** contents:

    [dropbox-uploads]
    src=/Users/username/Dropbox/Camera Uploads/
    dst=/Users/username/Pictures/
    saveas={Year}/{Year}-{Month}-{Day}/{Name}
    method=move
    log=true
    overwrite=false
    enabled=true

### Cron Setup

1. Edit Cron:

    `$ crontab -e`

2. Set process schedule for every 60 minutes:

    `*/60 * * * * python /Users/username/projects/pixif/pixif.py /Users/username/Dropbox/Camera\ Uploads/pixif.ini`

3. Save Cron.

After this process runs for the first time, `/Users/username/Dropbox/Camera Uploads/pixif.log` will contain a log of all pictures transferred using pixif.

### Equivalent Setup without Configuration File

Replace `/Users/username/Dropbox/Camera\ Uploads/pixif.ini` in step `2` above with:

    -src /Users/username/Dropbox/Camera\ Uploads/ -dst /Users/username/Pictures/ -a {Year}/{Year}-{Month}-{Day}/{Name} -m move -l

So that the full crontab entry is:

    */60 * * * * python /Users/username/projects/pixif/pixif.py -src /Users/username/Dropbox/Camera\ Uploads/ -dst /Users/username/Pictures/ -a {Year}/{Year}-{Month}-{Day}/{Name} -m move -l

