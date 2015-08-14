#!/usr/bin/env python3
"""
Helper for adding markdown doc files to git.

"""
import os

import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

md = markdown.Markdown()

def gitadd(filename):
    print('add:', f)
    call(['git', 'add', f])

if __name__ == '__main__':
    from subprocess import call, DEVNULL
    import sys

    from bs4 import BeautifulSoup

    assert len(sys.argv) > 1
    mdfile = sys.argv[1]
    basepath = os.path.dirname(mdfile)
    with open(mdfile) as f:
        data = f.read()
    html = md.convert(data)
    soup = BeautifulSoup(html, 'html.parser')
    images = [i.attrs['src'] for i in soup.findAll('img')]

    files = [mdfile] + [os.path.join(basepath, i) for i in images]

    new = call(['git', 'ls-files', mdfile, '--error-unmatch'], stderr=DEVNULL)

    for f in files:
        gitadd(f)
        if '-stamped' in f:
            f = f.replace('-stamped', '')
            gitadd(f)
            filename, ext = os.path.splitext(f)
            f = f.replace(ext, '-tags.txt')
            gitadd(f)

    tag, ext = os.path.splitext(mdfile)
    if new:
        message = '%s: Add documentation' % tag
    else:
        message = '%s: Update documentation' % tag
    call(['git', 'commit', '--author', 'Ajda', '-m', message])
