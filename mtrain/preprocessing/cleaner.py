#!/usr/bin/env python3

from mtrain.constants import *

'''
Replaces or cleans characters with special meaning in Moses or Nematus.
'''

def clean(segment):
    '''
    @param segment segment to be cleaned
    '''
    return segment # no additional cleaning by now

def escape_special_chars(segment):
    '''
    Escapes characters in @param segment with special meaning in Moses.
    '''
    for char, replacement in MOSES_SPECIAL_CHARS.items():
        segment = segment.replace(char, replacement)
    return segment

def deescape_special_chars(segment):
    '''
    Deespaces characters in @param segment with special meaning in Moses.
    '''
    for char in reversed(list(MOSES_SPECIAL_CHARS)): # ugly, but needed for python 3.4.2
        segment = segment.replace(MOSES_SPECIAL_CHARS[char], char)
    return segment

def normalize_romanian(segment):
    '''
    From script https://github.com/rsennrich/wmt16-scripts/blob/master/preprocess/normalise-romanian.py
    Author: Barry Haddow, Distributed under MIT license
    "Normalise Romanian s-comma and t-comma"
    when processing @param segment for backend nematus

    ###BH todo check reference above AND add reference to:
        wmt instructions https://github.com/rsennrich/wmt16-scripts/blob/master/sample/README.md
        wmt preprocess.sh
    '''
    # See http://www.fileformat.info/info/unicode/char:
    # tested ok, e.g. 'Iniţiaţi' with cedilla replaced by 'Inițiați' with comma below
    segment = segment.replace("\u015e", "\u0218").replace("\u015f", "\u0219")
    segment = segment.replace("\u0162", "\u021a").replace("\u0163", "\u021b")
    return segment

def remove_ro_diacritics(segment):
    '''
    From script https://github.com/rsennrich/wmt16-scripts/blob/master/preprocess/remove-diacritics.py
    Author: Barry Haddow, Distributed under MIT license
    "Remove Romanian diacritics. Assumes s-comma and t-comma are normalised"
    when processing @param segment for backend nematus

    ###BH todo check reference above AND add reference to:
        wmt instructions https://github.com/rsennrich/wmt16-scripts/blob/master/sample/README.md
        wmt preprocess.sh
    '''
    # See http://www.fileformat.info/info/unicode/char:
    # tested ok, e.g. 'Adică' replaced by 'Adica'
    segment = segment.replace("\u0218", "S").replace("\u0219", "s") #s-comma
    segment = segment.replace("\u021a", "T").replace("\u021b", "t") #t-comma
    segment = segment.replace("\u0102", "A").replace("\u0103", "a")
    segment = segment.replace("\u00C2", "A").replace("\u00E2", "a")
    segment = segment.replace("\u00CE", "I").replace("\u00EE", "i")
    return segment
