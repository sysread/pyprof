from cStringIO import StringIO
from cgi import escape as e


class Table(object):
    def __init__(self, title=None):
        self.title = title
        self.cols = []
        self.col_style = {}
        self.col_header_style = {}
        self.num_cols = 0
        self.data = []

    def add_column(self, name, style=None, header_style=None):
        self.cols.append(name)
        self.col_style[name] = style
        self.col_header_style[name] = header_style
        self.num_cols += 1

    def add_row(self, *values):
        self.data.append(values)

    def to_string(self):
        buf = StringIO()
        buf.write('<table border="0" cellpadding="0" cellspacing="0">')

        buf.write('<thead><tr>')
        for col in self.cols:
            if self.col_header_style[col] is not None:
                buf.write('<th class="%s">' % e(self.col_header_style[col]))
            else:
                buf.write('<th>')
            buf.write(e(col))
            buf.write('</th>')
        buf.write('</tr></thead><tbody>')

        counter = 1
        for row in self.data:
            style = ' class="even"' if counter % 2 == 0 else ''
            counter += 1

            buf.write('<tr%s>' % style)
            for i in xrange(self.num_cols):
                if i < len(row):
                    col = self.cols[i]
                    if self.col_style[col] is not None:
                        buf.write('<td class="%s">' % e(self.col_style[col]))
                    else:
                        buf.write('<td>')

                    buf.write(row[i])
                    buf.write('</td>')
            buf.write('</tr>')

        buf.write('</tbody></table>')
        return buf.getvalue()


class List(object):
    def __init__(self, style=None):
        self.style = style
        self.items = []

    def add(self, item):
        self.items.append(item)

    def to_string(self):
        buf = StringIO()

        if self.style:
            buf.write('<ul class="%s">' % self.style)
        else:
            buf.write('<ul>')

        for item in self.items:
            buf.write('<li>%s</li>' % item)

        buf.write('</ul>')
        return buf.getvalue()
