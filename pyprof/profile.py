from __future__ import division
import os
import pstats
from reports import HTMLReport


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

    def build_report(self, format='html', *args, **kwargs):
        dispatch = { 'html': HTMLReport }
        if format not in dispatch:
            raise ValueError('Output format not known: %s' % format)

        report = dispatch[format](*args, **kwargs)
        for raw_location, raw_calls in self.stats.stats.iteritems():
            location = self.make_location(raw_location)
            call = self.make_call(raw_calls)
            report.record_call(location, call)
        return report


if __name__ == '__main__':
    file_name = '/Volumes/devel/cms_dev/src/adgeletti_profile_data'
    profile = Profile(file_name)
    profile.add_search_path('/Volumes/devel/cms_dev/src')
    profile.add_rewrite_rule('/opt/devel', '/Volumes/devel')
    report = profile.build_report(format='html', colorize=True)
    report.generate('../output')
