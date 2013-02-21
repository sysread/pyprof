from __future__ import division
import os
import re
from cgi import escape as e
from collections import defaultdict
from html import Table, List
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer


class Report(object):
    COOL = 0
    WARM = 1
    HOT = 2

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

    def generate(self):
        raise NotImplementedError()


class HTMLReport(Report):
    def __init__(self, colorize=True):
        super(HTMLReport, self).__init__()
        self._colorize = colorize

    def colorize(self, line):
        if self._colorize:
            return highlight(line, PythonLexer(), HtmlFormatter())
        else:
            return '<pre>%s</pre>' % line

    def colorize_css(self):
        if self._colorize:
            return HtmlFormatter().get_style_defs('.highlight')
        return ''

    def css(self):
        return """
            tr.even { background-color: #eee }
            td, th { text-align: left; vertical-align: top; padding: 2px 4px; }
            th { border-bottom: 1px solid; padding-bottom: 6px; }
            .data { text-align: right; border-right: 1px solid; }
            ul.callers { margin: 0 0 0 32px; background-color: #FFFFB2; }
            ul.callers li { font-style: oblique; }
            ul.callees { margin: 0 0 0 32px; background-color: #CCFFEB; }
            ul.callees li { font-style: oblique; }
            pre { display: inline }
        """

    def header(self, title):
        return """
<html>
<head>
    <title>%s</title>
    <style type="text/css">
        %s
        %s
    </style>
</head>
<body>
    <h1>%s</h1>
        """ % (e(title), self.css(), self.colorize_css(), e(title))

    def footer(self):
        return '</body></html>'

    def generate(self, directory):
        output = os.path.normpath(directory)
        if not os.path.isdir(output):
            raise ValueError('Invalid output directory: %s' % directory)

        self.generate_index(output)
        for path in self.callees.keys():
            self.generate_file(output, path)

    def generate_index(self, directory):
        index_file = os.path.join(directory, 'index.html')
        with open(index_file, 'w') as html:
            html.write(self.header(title='Profiler Report'))
            html.write('<h2>Usage by file</h2>')

            table = Table()
            table.add_column('Exclusive', style='data')
            table.add_column('Inclusive', style='data')
            table.add_column('File')

            paths = sorted(self.callees.keys(), key=self.get_file_time)
            paths.reverse()

            for path in paths:
                link = Report.output_file(path, 'html')
                table.add_row(
                    '%0.05f' % self.file_time_spent_exc[path],
                    '%0.05f' % self.file_time_spent_inc[path],
                    '<a href="%s">%s</a>' % (link, e(path)),
                )

            html.write(table.to_string())
            html.write(self.footer())

    def generate_file(self, directory, path):
        out_file = os.path.join(directory, Report.output_file(path, 'html'))
        with open(out_file, 'w') as html:
            html.write(self.header(title='Page report: %s' % path))

            # Summary
            table = Table()
            table.add_column('Exclusive', style='data')
            table.add_column('Per call (exc)', style='data')
            table.add_column('Inclusive', style='data')
            table.add_column('Per call (inc)', style='data')
            table.add_column('Line', style='data')
            table.add_column('Callee')

            key_fn = lambda loc: self.call[loc].exclusive
            callees = sorted(self.callees[path], key=key_fn)
            callees.reverse()

            for callee in callees:
                call = self.call[callee]
                table.add_row(
                    '%f' % call.exclusive,
                    '%f' % call.exclusive_time_per_call,
                    '%f' % call.inclusive,
                    '%f' % call.inclusive_time_per_call,
                    '%d' % callee.line,
                    '<a href="#%d">%s</a>' % (callee.line, e(callee.func)),
                )

            html.write(table.to_string())

            # Code
            if os.path.isfile(path):
                html.write('<h2>Source</h2>')

                with open(path, 'r') as src:
                    table = Table()
                    table.add_column('Calls', style='data')
                    table.add_column('Exclusive time', style='data')
                    table.add_column('Per call (exc)', style='data')
                    table.add_column('Inclusive time', style='data')
                    table.add_column('Per call (inc)', style='data')
                    table.add_column('Line', style='data')
                    table.add_column('Source')

                    line_no = 1
                    for line in iter(src):
                        call = None

                        row = []
                        if path in self.call_at and line_no in self.call_at[path]:
                            call = self.call_at[path][line_no]
                            row = ['%d' % call.ncalls,
                                   '%f' % call.exclusive, '%f' % call.exclusive_time_per_call,
                                   '%f' % call.inclusive, '%f' % call.inclusive_time_per_call]
                        else:
                            row = ['&nbsp;'] * 5

                        row.append('%d' % line_no)
                        source = '<a name="%d" />%s' % (line_no, self.colorize(line))

                        if call is not None and call.has_callers:
                            callers = List(style='callers')
                            for call in call.callers:
                                link = Report.output_file(call.get_path(), 'html')
                                callers.add('called by <a href="%s#%d">%s</a>' % (
                                    link,
                                    call.line,
                                    e(call.func),
                                ))

                            source += callers.to_string()

                        if path in self.called_to and line_no in self.called_to[path]:
                            callees = List(style='callees')
                            loc = self.called_to[path][line_no]
                            link = Report.output_file(loc.get_path(), 'html')
                            callees.add('calls <a href="%s#%d">%s</a>' % (
                                    link,
                                    loc.line,
                                    e(loc.func),
                                ))
                            source += callees.to_string()

                        row.append(source)
                        table.add_row(*row)
                        line_no += 1

                    html.write(table.to_string())

            html.write(self.footer())
