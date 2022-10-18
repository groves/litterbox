#!/usr/bin/env python
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import functools
import os
import re
import signal
import socket
import subprocess
import sys
from typing import Callable
from urllib.parse import quote_from_bytes


@functools.cache
def hostname():
    return socket.gethostname().encode('utf-8')
    
def write_hyperlink(write: Callable[[bytes], None], path: str, line: bytes, frag: bytes = b'') -> None:
    path = quote_from_bytes(os.path.abspath(path)).encode('utf-8')
    text = b'\033]8;;file://' + hostname() + path
    if frag:
        text += b'#' + frag
    text += b'\033\\' + line + b'\033]8;;\033\\'
    write(text)


def consume_process(p, line_handler, write=None):
    if write is None:
        def write(b):
            sys.stdout.buffer.write(b)
            # If we're in a pipe, we'll not have a tty and be block buffered
            # Flush to avoid that.
            # Can't easily turn off block buffering from inside the program
            # https://stackoverflow.com/questions/881696/unbuffered-stdout-in-python-as-in-python-u-from-within-the-program
            sys.stdout.buffer.flush()
    sgr_pat = re.compile(br'\x1b\[.*?m')
    osc_pat = re.compile(b'\x1b\\].*?\x1b\\\\')
    try:
        for line in p.stdout:
            line = osc_pat.sub(b'', line)  # remove any existing hyperlinks
            clean_line = sgr_pat.sub(b'', line).rstrip()  # remove SGR formatting
            line_handler(write, line, clean_line)
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
    except (EOFError, BrokenPipeError):
        pass
    finally:
        try:
            stream.close()
        except:
            pass
    return p.wait()

def main(argv, write=None):
    if not sys.stdout.isatty() and '--pretty' not in argv and '-p' not in argv:
        os.execlp('rg', 'rg', *argv[1:])

    in_result: bytes = [b'']
    num_pat = re.compile(br'^(\d+):')
    def line_handler(write, raw_line, clean_line):
        if in_result[0]:
            m = num_pat.match(clean_line)
            if not clean_line:
                in_result[0] = b''
            elif m := num_pat.match(clean_line):
                write_hyperlink(write, in_result[0], raw_line, frag=m.group(1))
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



if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
