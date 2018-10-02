import io
import shlex
from contextlib import redirect_stderr

import cmd2
import functools

from .interfaces import wopen_parser, course_query_or_cc, catann_parser
from .utils import unique_course_code, filter_courses


def complete_any(text, line, begidx, endidx, completers):
    for completer in completers:
        completions = completer(text, line, begidx, endidx)
        if completions:
            return completions
    return []


def parse_partial(argparser, line):
    try:
        stream = io.StringIO()
        with redirect_stderr(stream):
            opts, _ = argparser.parse_known_args(shlex.split(line)[1:])
            return opts
    except ValueError as e:
        if str(e) == 'No closing quotation':
            print(line + '\'')
            return parse_partial(argparser, line + '\'')
    except:
        import traceback
        traceback.print_exc()
        return None


class Completers():
    def __init__(self, clanvas):
        self.clanvas = clanvas
        self._course_complete_flags = dict.fromkeys(['-c', '--course'], self.course_completer)

    def course_completer(self, text, line, begidx, endidx):
        return list(map(unique_course_code, filter_courses(self.clanvas.get_courses().values(), line[begidx:endidx])))

    def catann_tab_completer(self, text, line, begidx, endidx):
        opts = parse_partial(catann_parser, line)
        if opts is None:
            return []

        opts.course = course_query_or_cc(self.clanvas, opts.course, fail_on_ambiguous=True, quiet=True)

        if opts.course is None:
            return []

        announcements = list(opts.course.get_discussion_topics(only_announcements=True))


        matched_announcements = list(filter(lambda ann: str(ann.id).startswith(str(opts.id[0])), announcements))

        items = list(map(lambda ann: str(ann.id), matched_announcements))

        return items

    def wopen_tab_completer(self, text, line, begidx, endidx):
        opts = parse_partial(wopen_parser, line)
        if opts is None:
            return []

        opts.course = course_query_or_cc(self.clanvas, opts.course, fail_on_ambiguous=True, quiet=True)
        if opts.course is None:
            return []

        tabs = self.clanvas.list_tabs_cached(opts.course.id)
        matched_tabs = filter(lambda tab: tab.label.lower().startswith(opts.tab.lower()), tabs)
        return list(map(lambda tab: shlex.quote(tab.label.lower()), matched_tabs))

    def generic_course_optional_completer(self, text, line, begidx, endidx, default_completer=None):
        return self.clanvas.flag_based_complete(text, line, begidx, endidx, flag_dict=self._course_complete_flags,
                                                all_else=default_completer)

    def catann_completer(self, text, line, begidx, endidx):
        return self.clanvas.flag_based_complete(text, line, begidx, endidx, flag_dict=self._course_complete_flags,
                                                all_else=self.catann_tab_completer)

    def wopen_completer(self, text, line, begidx, endidx):
        return self.clanvas.flag_based_complete(text, line, begidx, endidx, flag_dict=self._course_complete_flags,
                                                all_else=self.wopen_tab_completer)

    def pullf_completer(self, text, line, begidx, endidx):
        output_flags = dict.fromkeys(['-o', '--output'], functools.partial(self.clanvas.path_complete, dir_only=True))
        return self.clanvas.flag_based_complete(text, line, begidx, endidx, flag_dict={
            **self._course_complete_flags,
            **output_flags})
