#!/usr/bin/env python
import os
from optparse import OptionParser
from pyprof import Profile

parser = OptionParser()
parser.add_option('-d', dest='datafile', type='string', help='python profiler data file')
parser.add_option('-o', dest='output_dir', type='string', default='.', help='output directory for data files (default: current directory)')
parser.add_option('-f', dest='format', type='choice', default='html', choices=['html'], help='output format (default: html)')
parser.add_option('-c', dest='colorize', type='int', default=True, help='colorize HTML output (ignored when format is not html)')
parser.add_option('-I', dest='include', type='string', default='', help='include path, separated by colons')
parser.add_option('-r', dest='replace', type='string', default='', help='path replacements (e.g. /usr/lib=/optlib), separated by colons')
(options, args) = parser.parse_args()

def error(msg):
    print 'Error: %s\n' % msg
    parser.print_help()
    print '\n'
    exit(1)

#-------------------------------------------------------------------------------
# Check options
#-------------------------------------------------------------------------------
if not options.datafile:
    error('datafile is required')

if not os.path.isfile(options.datafile):
    error('datafile not found')

if not os.path.isdir(options.output_dir):
    error('output directory not found')

if options.include:
    options.include = options.include.split(':')

if options.replace:
    replace = {}
    for pair in options.replace.split(':'):
        (k, v) = pair.split('=')
        replace[k] = v
    options.replace = replace

#-------------------------------------------------------------------------------
# Configure profile
#-------------------------------------------------------------------------------
print 'Reading profiling data'
profile = Profile(options.datafile)

if options.include:
    for inc in options.include:
        print 'Adding search path: %s' % inc
        profile.add_search_path(inc)

if options.replace:
    for k, v in options.replace.items():
        print 'Adding rewrite rule: "%s" => "%s"' % (k, v)
        profile.add_rewrite_rule(k, v)

#-------------------------------------------------------------------------------
# Build report
#-------------------------------------------------------------------------------
print 'Preparing report'
report_args = { 'format': options.format }
if options.format == 'html':
    report_args['colorize'] = options.colorize

report = profile.build_report(**report_args)

print 'Generating report (%s)' % (options.format)
report.generate(options.output_dir)

print 'Done!'
exit(0)
