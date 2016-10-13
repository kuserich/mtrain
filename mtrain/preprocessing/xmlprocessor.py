#!/usr/bin/env python3

'''
Class for handling XML markup during training and translation
'''

from mtrain.preprocessing.masking import Masker
from mtrain.constants import *

import re
from lxml import etree

class XmlProcessor(object):
    '''
    Process XML markup properly before training, and before
        and after translation.
    '''
    def __init__(self, markup_strategy):
        self._markup_strategy = markup_strategy

    def _strip_markup(self, segment):
        '''
        Removes all XML markup from a segment and normalizes
            whitespace between tokens before returning.
        @param segment the string from which XML markup
            should be removed
        '''
        # unescaped markup
        if '<' in segment:
            tree = etree.fromstring('<root>' + segment + '</root>')
            segment  = etree.tostring(tree, encoding='unicode', method='text')
        # markup that was escaped in the original segment, now surfaced
        if '<' in segment:        
            segment = re.sub('<[^>]*>', '', segment)
            segment = re.sub(' +', ' ', segment)

        return segment

    def _mask_markup(self, segment):
        '''
        Replaces XML markup with mask tokens.
        @param segment the segment to be masked
        @return the masked segment and the mapping
            between mask tokens and original content
        '''
        pass

    def _unmask_markup(self, segment, mapping):
        '''
        When a mask token is found, reinsert the original
            XML markup content.
        @param segment a segment with mask tokens
        @param mapping a dictionary containing the mask tokens
            and the original content
        '''
        pass

    def _restore_markup(self, segment, original):
        '''
        Restores XML markup in a segment where markup was
            stripped before translation.
        @param segment a segment stripped of markup
        @param original the original segment in the source language
            before XML markup was removed
        '''
        pass

    def _force_mask_translation(self, masked_segment):
        '''
        Turns mask tokens into forced translation directives which
            ensure that Moses translates mask tokens correctly.
        @param masked_segment an untranslated segment with mask tokens
        '''
        pass

    # Exposed methods
    def preprocess_markup(self, segment):
        '''
        Strips or masks XML markup before translation, depending
            on the markup strategy.
        '''
        # do something, depending on strategy
        pass

    def postprocess_markup(self, segment):
        '''
        Unmasks or restores XML markup after translation, depending
            on the markup strategy.
        '''
        # do something, depending on strategy
        pass
