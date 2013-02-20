from __future__ import division
import os
import pstats
import re
from cgi import escape as e
from collections import defaultdict
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter


class Location(object):
    __slots__ = ('path', 'line', 'func', 'abs_path')

    def __init__(self, path, line, func):
        self.path = path
        self.line = line
        self.func = func
        self.abs_path = None

    def get_path(self):
        if self.is_built_in:
            return '[built in]'
        elif self.is_eval:
            return '[eval]'
        else:
            return self.abs_path or self.path

    @property
    def is_built_in(self):
        return self.path == '~'

    @property
    def is_eval(self):
        return self.path == '<string>'


class Call(object):
    __slots__ = ('pcalls', 'ncalls', 'exclusive', 'inclusive', 'callers')

    def __init__(self, pcalls, ncalls, exclusive, inclusive):
        self.pcalls = pcalls
        self.ncalls = ncalls
        self.exclusive = exclusive
        self.inclusive = inclusive
        self.callers = []

    def add_caller(self, caller):
        self.callers.append(caller)

    @property
    def is_recursive(self):
        return self.pcalls != self.ncalls

    @property
    def exclusive_time_per_call(self):
        return self.exclusive / self.ncalls

    @property
    def inclusive_time_per_call(self):
        return self.inclusive / self.ncalls

    @property
    def has_callers(self):
        return self.callers is not None


class Profile(object):
    def __init__(self, profiler_data):
        self.stats = pstats.Stats(profiler_data)
        self.search = []
        self.rewrite = {}

    def add_search_path(self, path):
        self.search.append(path)

    def add_rewrite_rule(self, prefix, replacement):
        self.rewrite[prefix] = replacement

    def resolve_path(self, target):
        for prefix, replacement in self.rewrite.iteritems():
            if target.startswith(prefix):
                target = target.replace(prefix, replacement)

        if os.path.exists(target) and os.path.isfile(target):
            return os.path.normpath(target)

        for search_path in self.search:
            path = os.path.join(search_path, target)
            if os.path.exists(path) and os.path.isfile(path):
                return path

        raise ValueError('Path not found: %s' % target)

    def make_location(self, location_tuple):
        location = Location(*location_tuple)
        if not location.is_built_in and not location.is_eval:
            location.abs_path = self.resolve_path(location.path)
        return location

    def make_call(self, call_data):
        (pcalls, ncalls, exclusive, inclusive, callers) = call_data
        call = Call(pcalls, ncalls, exclusive, inclusive)
        for caller in callers:
            location = self.make_location(caller)
            call.add_caller(location)
        return call

    def build_report(self):
        report = Report()
        for raw_location, raw_calls in self.stats.stats.iteritems():
            location = self.make_location(raw_location)
            call = self.make_call(raw_calls)
            report.record_call(location, call)
        return report


class Report(object):
    def __init__(self):
        # Location data
        self.callees = defaultdict(set) # location set by path

        # Call data
        self.call = {}
        self.call_at = defaultdict(dict) # callee by path and line
        self.called_to = defaultdict(dict) # caller by path and line

        # Aggregate file summary data
        self.file_time_spent_inc = defaultdict(int)
        self.file_time_spent_exc = defaultdict(int)

    def record_call(self, location, call):
        path = location.get_path()
        self.callees[path].add(location)
        self.call[location] = call
        self.file_time_spent_inc[path] += call.inclusive
        self.file_time_spent_exc[path] += call.exclusive

        self.call_at[path][location.line] = call
        if call.has_callers:
            for c in call.callers:
                self.called_to[c.get_path()][c.line] = location

    @staticmethod
    def output_file(path, ext):
        ext = ext.strip('.')
        output_file = re.sub(r'[^-_a-zA-Z0-9]', '_', path)
        output_file = output_file.strip('_') + '.' + ext
        return output_file

    def get_file_time(self, path):
        if path in self.file_time_spent_exc:
            return self.file_time_spent_exc[path]
        else:
            return 0

    def generate_html(self, directory):
        output = os.path.normpath(directory)
        if not os.path.isdir(output):
            raise ValueError('Invalid output directory: %s' % directory)

        self.generate_index(output)
        for path in self.callees.keys():
            self.generate_file(output, path)

    def generate_index(self, directory):
        index_file = os.path.join(directory, 'index.html')
        with open(index_file, 'w') as html:
            html.write('<html><head><title>Profiler Report</title></head>')
            html.write('<body>')
            html.write('<h1>Profiler Report</h1>')

            html.write('<h2>Usage by file</h2>')
            html.write('<table>')
            html.write('<thead>')
            html.write('<tr>')
            html.write('<th>File</th>')
            html.write('<th>Exclusive</th>')
            html.write('<th>Inclusive</th>')
            html.write('</tr>')
            html.write('</thead>')
            html.write('<tbody>')

            paths = sorted(self.callees.keys(), key=self.get_file_time)
            paths.reverse()

            for path in paths:
                link = Report.output_file(path, 'html')
                html.write('<tr>')
                html.write('<td><a href="%s">%s</a></td>' % (link, e(path)))
                html.write('<td>%0.05f</td>' % self.file_time_spent_exc[path])
                html.write('<td>%0.05f</td>' % self.file_time_spent_inc[path])
                html.write('</tr>')

            html.write('</tbody>')
            html.write('</table>')

            html.write('</body></html>')

    def colorize(self, line):
        return highlight(line, PythonLexer(), HtmlFormatter())

    def colorize_css(self):
        return HtmlFormatter().get_style_defs('.highlight')

    def generate_file(self, directory, path):
        out_file = os.path.join(directory, Report.output_file(path, 'html'))
        with open(out_file, 'w') as html:
            html.write('<html><head><title>%s</title>\n' % e(path))
            html.write('<style type="text/css">')
            #html.write('body, table { font-size: 0.9em }')
            html.write('tr.even { background-color: #eee }')
            html.write('td, th { text-align: left; vertical-align: top; padding: 2px 4px; }')
            html.write('.data { text-align: right; border-right: 1px solid; }')
            html.write('ul.callers { margin: 0 0 0 32px; background-color: #FFFFB2; }')
            html.write('ul.callers li { font-style: oblique; }')
            html.write('ul.callees { margin: 0 0 0 32px; background-color: #CCFFEB; }')
            html.write('ul.callees li { font-style: oblique; }')
            html.write('pre { display: inline }')
            html.write(self.colorize_css())
            html.write('</style>')
            html.write('</head><body>')
            html.write('<h1>%s</h1>' % e(path))

            # Summary
            html.write('<table cellspacing="0" cellpadding="0" border="0">')
            html.write('<thead><tr>')
            html.write('<th class="data">Exclusive</th>')
            html.write('<th class="data">Inclusive</th>')
            html.write('<th class="data">Per call (exc)</th>')
            html.write('<th class="data">Line</th>')
            html.write('<th>Callee</th>')
            html.write('</tr></thead><tbody>')

            key_fn = lambda loc: self.call[loc].exclusive
            callees = sorted(self.callees[path], key=key_fn)
            callees.reverse()

            for callee in callees:
                call = self.call[callee]
                html.write('<tr>')
                html.write('<td class="data">%f</td>' % call.exclusive)
                html.write('<td class="data">%f</td>' % call.inclusive)
                html.write('<td class="data">%f</td>' % (call.exclusive / call.ncalls))
                html.write('<td class="data">%d</td>' % callee.line)
                html.write('<td><a href="#%d">%s</a></td>' % (callee.line, e(callee.func)))
                html.write('</tr>')

            html.write('</tbody>')
            html.write('</table>')

            # Code
            if os.path.isfile(path):
                with open(path, 'r') as src:
                    html.write('<h2>Source</h2>')
                    html.write('<table cellspacing="0" cellpadding="0" border="0">')
                    html.write('<thead>')
                    html.write('<tr>')
                    html.write('<th class="data">Calls</th>')
                    html.write('<th class="data">Exclusive time</th>')
                    html.write('<th class="data">Inclusive time</th>')
                    html.write('<th class="data">Per call (exc)</th>')
                    html.write('<th class="data">Line</th>')
                    html.write('<th>Source</th>')
                    html.write('</tr>')
                    html.write('</thead>')

                    html.write('<tbody>')
                    line_no = 1
                    for line in iter(src):
                        tr_class = 'even' if line_no % 2 == 0 else 'odd'
                        html.write('<tr class="%s">' % tr_class)
                        call = None

                        if path in self.call_at and line_no in self.call_at[path]:
                            call = self.call_at[path][line_no]
                            html.write('<td class="data">%d</td>' % call.ncalls)
                            html.write('<td class="data">%f</td>' % call.exclusive)
                            html.write('<td class="data">%f</td>' % call.inclusive)
                            html.write('<td class="data">%f</td>' % (call.exclusive / call.ncalls))
                        else:
                            html.write('<td class="data">&nbsp;</td>')
                            html.write('<td class="data">&nbsp;</td>')
                            html.write('<td class="data">&nbsp;</td>')
                            html.write('<td class="data">&nbsp;</td>')

                        html.write('<td class="data">%d</td>' % line_no)
                        html.write('<td><a name="%d" />%s' % (line_no, self.colorize(line)))

                        if call is not None and call.has_callers:
                            html.write('<ul class="callers">')
                            for call in call.callers:
                                link = Report.output_file(call.get_path(), 'html')
                                html.write('<li>called by %s - <a href="%s#%d">%s:%d</a></li>' % (
                                    e(call.func),
                                    link,
                                    call.line,
                                    e(call.get_path()),
                                    call.line,
                                ))
                            html.write('</ul>')

                        if path in self.called_to and line_no in self.called_to[path]:
                            loc = self.called_to[path][line_no]
                            link = Report.output_file(loc.get_path(), 'html')
                            html.write('<ul class="callees">')
                            html.write('<li>calls to %s - <a href="%s#%d">%s:%d</a></li>' % (
                                    e(loc.func),
                                    link,
                                    loc.line,
                                    e(loc.get_path()),
                                    loc.line,
                                ))
                            html.write('</ul>')

                        html.write('</td></tr>')
                        line_no += 1

                    html.write('</tbody>')
                    html.write('</table>')

            html.write('</body></html>')



if __name__ == '__main__':
    file_name = '/Volumes/devel/cms_dev/src/adgeletti_profile_data'
    profile = Profile(file_name)
    profile.add_search_path('/Volumes/devel/cms_dev/src')
    profile.add_rewrite_rule('/opt/devel', '/Volumes/devel')
    report = profile.build_report()
    report.generate_html('../output')
