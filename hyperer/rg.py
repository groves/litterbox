#!/usr/bin/env python
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>
import os
import re
import subprocess
import sys
from . import make_hyperlink, consume_process, strip_ansi

match_pat = re.compile(b'\x1b\\[31m(.+?)\x1b\\[0m')
def link_matches(line, path, line_num, prefix_width):
    # If we're able to find individual matches via their being colored, link to the column of each match
    last_match_end = 0
    for match in match_pat.finditer(line):
        yield line[last_match_end:match.start()]
        col_num = b'%d' % (len(strip_ansi(line[:match.start()])) + 1 - prefix_width)
        yield make_hyperlink(path, match.group(0),
            frag=line_num + b':' + col_num,
            params={b'line': line_num, b'column': col_num})
        last_match_end = match.end()
    if last_match_end > 0:
        yield line[last_match_end:]
    else: 
        # We didn't find a colored match, fall back to linking the whole line
        yield make_hyperlink(path, line, frag=line_num, params={b'line': line_num})

def main(argv=sys.argv, write=None):
    # TODO - skip urls if --json is given
    if not sys.stdout.isatty() and '--pretty' not in argv and '-p' not in argv:
        os.execlp('rg', 'rg', *argv[1:])

    # TODO - parse --colors to see if something other than red is being used for matches
    in_result: bytes = [b'']
    num_pat = re.compile(br'^(\d+):')
    def line_handler(write, raw_line, clean_line):
        if in_result[0]:
            m = num_pat.match(clean_line)
            if not clean_line:
                in_result[0] = b''
            elif m := num_pat.match(clean_line):
                write(b''.join(link_matches(raw_line, in_result[0], m.group(1), len(m.group(0)))))
                return
        elif raw_line.strip():
            in_result[0] = clean_line
        write(raw_line)

    cmdline = ['rg', '--pretty', '--with-filename'] + argv[1:]
    try:
        p = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
    except FileNotFoundError:
        raise SystemExit('Could not find the rg executable in your PATH. Is ripgrep installed?')

    return consume_process(p, line_handler, write)
