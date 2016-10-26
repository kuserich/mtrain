#!/usr/bin/env python3

'''
Class for replacing stretches of text with a mask token or
reversing this process.
'''

from mtrain.constants import *
from mtrain.preprocessing import cleaner

import re

class _Replacement(object):
    '''
    Track replacements in strings.
    Based on: http://stackoverflow.com/a/9135166/1987598
    '''
    def __init__(self, replacement, with_id=False):
        self.replacement = replacement
        self.occurrences = []
        self.with_id = with_id

    def __call__(self, match):
        matched = match.group(0)
        if self.with_id:
            replaced = match.expand(
                "__%s_%d__" % (self.replacement, len(self.occurrences))
            )
        else:
            replaced = match.expand(
                "__%s__" % self.replacement
            )
        self.occurrences.append((replaced, matched))
        return replaced

class Masker(object):
    
    def __init__(self, strategy, escape=True):
        '''
        @param strategy valid masking strategy
        @param escape whether characters reserved in Moses should be escaped
        '''
        self._strategy = strategy
        self._escape = escape

    def mask_segment(self, segment):
        '''
        Introduces mask tokens into segment and escapes characters.
        @param segment the input text
        '''
        mapping = []
        
        for mask_token, regex in PROTECTED_PATTERNS.items():        
            if self._strategy == MASKING_IDENTITY:
                replacement = _Replacement(mask_token, with_id=True)
            # currently, for all other strategies
            else:
                replacement = _Replacement(mask_token, with_id=False)
            segment = re.sub(regex, replacement, segment)
            mapping.extend(replacement.occurrences)
        
        if self._escape:
            segment = cleaner.escape_special_chars(segment)
    
        return segment, mapping
    
    def mask_tokens(self, tokens):
        masked_segment, mapping = self.mask_segment(" ".join(tokens))
        return masked_segment.split(" "), mapping
    
    def _mask_in_string(self, string):
        '''
        Determines whether there is a mask token in a string.
        '''
        for token in string.split(" "):
            if self._is_mask_token(token):
                return True

    def _is_mask_token(self, token):
        '''
        Determines whether an input @param token is a mask or not.
        '''
        # make sure token is a string
        token = str(token)
        
        for mask in PROTECTED_PATTERNS.keys():
            if self._strategy == MASKING_IDENTITY:
                return bool(re.match("__%s_\d+__" % mask, token))
            else:
                return token == "__%s__" % mask

    def _first_original(self, mask, mapping):
        '''
        Returns the original that belongs to the first occurrence of
            @param mask from @param mapping.
        @return the original and index of this tuple in the mapping
        '''
        for index, tuple in enumerate(mapping):
            token, original = tuple
            if token == mask:
                return original, index

    def unmask_segment(self, source_segment, target_segment, mapping, alignment=None, segmentation=None):
        '''
        Removes mask tokens from string and replaces them with their actual content.
        @param source_segment masked segment before translation
        @param target_segment text to be unmasked
        @param mapping list of tuples [(mask_token, original_content), ...]
        @param alignment word alignment reported by Moses, a dictionary with
            source indexes as keys 
        @param segmentation phrase segmentation reported by Moses, a dictionary
            with source index tuples as keys
        '''
        
        if mapping:
            # assume that info on word alignment is available
            if self._strategy == MASKING_ALIGNMENT:                
                mapping_masks = [tuple[0] for tuple in mapping]
                
                # no duplicate masks in the mapping?
                if len(mapping_masks) == len(set(mapping_masks)):
                    # then, same strategy as identity masking
                    for mask_token, original in mapping:
                        target_segment = target_segment.replace(mask_token, original, 1)
                else:
                    source_tokens = source_segment.split(" ")
                    target_tokens = target_segment.split(" ")
                    # go through source tokens
                    for source_index, source_token in enumerate(source_tokens):
                        if self._is_mask_token(source_token):
                            found_match = False
                            # follow alignment to target token(s)
                            for candidate_index in alignment[source_index]:
                                # determine aligned token in target phrase
                                target_token = target_tokens[candidate_index]
                                if self._is_mask_token(target_token):
                                    # then, finally reinsert original content
                                    target_tokens[candidate_index], remove_index = self._first_original(source_token, mapping)
                                    del mapping[remove_index]
                                    
                                    found_match = True
                                    # immediately break out, do not check other aligned candidates in the target phrase
                                    break

                            if not found_match:
                                logging.debug(
                                    "Unmasking for source mask %s failed. " % source_token
                                    + "Mask is missing in the target phrase or in mapping."
                                )
                    # and if masks are left in the mapping that could not be assigned
                    if mapping:
                        logging.debug(
                            "One or more masks in the mapping were not used for unmasking: %s" % str(mapping)
                        )
                    target_segment = " ".join(target_tokens)

            elif self._strategy == MASKING_IDENTITY:
                for mask_token, original in mapping:
                    target_segment = target_segment.replace(mask_token, original, 1)

        # check if there are still masks in the target segment
        if self._mask_in_string(target_segment):
            logging.debug(
                "Target segment: '%s' still contains mask tokens after unmasking." % target_segment
            )
                    
        return target_segment

def write_masking_patterns(protected_patterns_path):
    '''
    Writes protected patterns to a physical file in the engine directory.
    @param protected_patterns_path path to file the patterns should be written to
    '''
    with open(protected_patterns_path, 'w') as patterns_file:
        for mask_token, regex in PROTECTED_PATTERNS.items():
            patterns_file.write("# %s\n%s\n" % (mask_token, regex))

def force_mask_translation(segment):
    '''
    Turns mask tokens into forced translation directives which
        ensure that Moses translates mask tokens correctly.
    @param masked_segment an untranslated segment that probably
        has mask tokens
    '''
    pattern = re.compile('__.+__')
    for mask_token in re.findall(pattern, segment):
        replacement = '<mask translation="%s">%s</mask>' % (mask_token, mask_token)
        segment = segment.replace(mask_token, replacement)

    return segment
