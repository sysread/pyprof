NAME
----
pyprof - a report generator for python profiling data

SYNOPSIS
--------
`pyprof_report -d datafile [-o output_dir] [-f html] [-c 1]`

DESCRIPTION
-----------
`pyprof` generates reports from data files created using the [Python
profiler](http://docs.python.org/2.7/library/profile.html). Report data
summarizes performance by file with individual pages for each source file,
making it much easier to visualize the performance of individual functions.

EXAMPLES
--------
Profile your software:
    python -m cProfile -o profiler_data my_app.py
