#!/usr/bin/env python3

from mtrain.constants import *

from collections import defaultdict
from lxml import etree

import xml.sax
import re
import sys

'''
Reinsert markup into target segments, based on the markup found in the source segments.
'''

class Reinserter(object):
    '''
    Class for reinserting markup into segments that were stripped of
        markup prior to translation.
    '''

    def __init__(self, reinsertion_strategy, force_all=True):
        '''
        @param reinsertion_strategy the method for reinsertion
        @param force_all whether all tags found in the source must by all means be
            inserted into the target segment, even if there is no conclusive evidence
        '''
        self._reinsertion_strategy = reinsertion_strategy
        self._force_all = force_all

    def _next_source_tag_region(self, source_tokens):
        '''
        Generates lists of source token indexes that are bounded by an opening
            and closing tag.
        @return a list of indexes if a region is found, until the generator is exhausted
        '''
        while _tag_in_list(source_tokens):
            current_indexes = []
            current_opening_tag = None        
            tags_seen_offset = 0
            
            for source_index, source_token in enumerate(source_tokens):
                if _is_selfclosing_tag(source_token):
                    # yield and break, no content
                    del source_tokens[source_index]
                    yield (source_index - tags_seen_offset, source_token), [], None
                    break
                elif _is_closing_tag(source_token):
                    # delete this pair of tags from the source
                    del source_tokens[source_index]
                    try:
                        del source_tokens[current_opening_tag[0]]
                    except TypeError:
                        print(source_tokens)
                        sys.exit()
                    # then yield, because the closing tag is bound to correspond to
                    # the most recent opening tag
                    yield (current_opening_tag[0] - tags_seen_offset, current_opening_tag[1]), \
                        current_indexes, (source_index - tags_seen_offset, source_token)
                    break            
                elif _is_opening_tag(source_token):
                    tags_seen_offset += 1
                    # then reset current indexes and tags
                    current_indexes = []
                    current_opening_tag = source_index, source_token
                else:
                    if current_opening_tag:
                        # then add to indexes
                        current_indexes.append(source_index - tags_seen_offset)
                    # else, do nothing; not yet in a source tag region

    def _find_source_phrase_regions(self, source_tag_region, segmentation):
        '''
        Given a source tag region and segmentation, determines the source phrases
            the source tag region is in.
        @param source_tag_region a list of indexes that identify a source tag region
        @param segmentation phrase segmentation reported by Moses, a dictionary
            where keys are tuples of source spans
        @return a sorted list of tuples, a subset of @param segmentation
        '''
        source_phrase_region = []

        for start, end in segmentation:
            phrase_collected = False
            # one of the tokens of the source tag region in this phrase?
            for index in source_tag_region:
                if int(start) <= index <= int(end):
                    source_phrase_region.append( (start, end) )
                    phrase_collected = True
                    # break early because there is enough evidence already
                    break
            if source_phrase_region and not phrase_collected:
                # break early because source phrase region must be contiguous
                break

        return sorted(source_phrase_region)

    def _find_target_covering_phrases(self, source_phrase_regions, segmentation):
        '''
        Finds the phrases in the target phrase that were used to translate the source
            phrase regions.
        @param source_phrase_regions list of source phrases that encompass the current
            source tag region
        @param segmentation phrase segmentation reported by Moses, a dictionary
            where keys are tuples of source spans
        '''
        target_covering_phrases = []

        for tuple in source_phrase_regions:
            target_covering_phrases.append(segmentation[tuple])

        return target_covering_phrases

    def _str_spr_coincide(self, source_tag_region, source_phrase_regions):
        '''
        Returns true if the boundaries of the source tag region coincide with the first
            starting index of the source_phrase_regions, and with their last ending index
        '''
        # source_phrase_regions must be sorted
        if ( source_tag_region[0] == source_phrase_regions[0][0] and
            source_tag_region[-1] == source_phrase_regions[-1][1]) :
            return True
        else:
            return False

    def _tcp_is_contiguous(self, target_covering_phrases):
        '''
        Determine whether the target covering phrases are contiguous.
        @param target_covering_phrases a list of tuples with index spans
        '''
        last_tuple = ()
        for start, end in target_covering_phrases:
            if not last_tuple:
                last_tuple = (start, end)
            # if start of phrase not immediately adjacent to last phrase
            elif last_tuple[1] != start - 1:
                return False
            else:
                last_tuple = (start, end)

        # if you made it thus far, then
        return True

    def _reinsert_markup_full(self, source_segment, target_segment, segmentation, alignment):
        '''
        Reinserts markup, taking into account both phrase segmentation and word alignment.
        @param source_segment the original segment in the source language
            before XML markup was removed, but after markup-aware tokenization
        @param target_segment a translated segment without markup
        @param segmentation phrase segmentation reported by Moses, a dictionary
            where keys are tuples of source spans
        @param alignment word alignment information reported by Moses, a
            dictionary where source tokens are keys
        '''
        source_tokens = tokenize_keep_markup(source_segment)
        target_tokens = target_segment.split(" ")

        changes = []
        
        str_generator = self._next_source_tag_region(source_tokens)
        
        for opening, source_tag_region, closing in str_generator:
            opening_index, opening_tag = opening[0], opening[1]
            
            if not closing:
                # selfclosing tag
                try:
                    changes.append( (alignment[opening_index][0], opening_tag) )
                except IndexError:
                    changes.append( (len(target_tokens), opening_tag) )

            elif not source_tag_region:
                # tag pair with no content tokens between them
                closing_tag = closing[1]
                insert_at = alignment[opening_index][0] + 1

                changes.append(
                    (insert_at, " ".join( [opening_tag, closing_tag]) )
                )
            else:
                closing_tag = closing[1]

                source_phrase_regions = self._find_source_phrase_regions(source_tag_region, segmentation)
                target_covering_phrases = self._find_target_covering_phrases(source_phrase_regions, segmentation)

                if self._str_spr_coincide(source_tag_region, source_phrase_regions):
                    if self._tcp_is_contiguous(target_covering_phrases):
                        # Rule 1
                        changes.append(
                            (target_covering_phrases[-1][1] + 1, closing_tag)
                        )
                        changes.append(
                            (target_covering_phrases[0][0], opening_tag)
                        )
                        
                    else:
                        # Rule 3
                        changes.append(
                            (min(target_covering_phrases, key=lambda x: x[0])[0], opening_tag)
                        )
                        changes.append(
                            (max(target_covering_phrases, key=lambda x: x[1])[1] + 1, closing_tag)
                        )
                else:
                    # rely on word alignments in this part
                    relevant_alignments = []
                    for index in source_tag_region:
                        relevant_alignments.extend(alignment[index])

                    if self._tcp_is_contiguous(target_covering_phrases):
                        # Rule 2
                        try:
                            insert_at_opening = min(relevant_alignments)
                        except ValueError:
                            insert_at_opening = len(target_tokens)
                        changes.append(
                            (insert_at_opening, opening_tag)
                        )
                        try:
                            insert_at_closing = max(relevant_alignments) + 1
                        except ValueError:
                            insert_at_closing = len(target_tokens) + 1
                        changes.append(
                            (insert_at_closing, closing_tag)
                        )
                    else:
                        # Rule 3.5
                        # find leftmost and rightmost TCP
                        left_start, left_end = min(target_covering_phrases, key=lambda x: x[0])
                        right_start, right_end = max(target_covering_phrases, key=lambda x: x[1])

                        for index in range(left_start, left_end+1):
                            if index in relevant_alignments:
                                changes.append( (index, opening_tag) )
                                break
                        for index in reversed(range(right_start, right_end + 1)):
                            if index in relevant_alignments:
                                changes.append( (index, closing_tag) )
                                break

        # then, actually make changes in reverse order
        for insert_at, tag in sorted(changes, key=lambda x: x[0], reverse=True):
            target_tokens.insert(insert_at, tag)

        return " ".join(target_tokens)

    def _reinsert_markup_segmentation(self, source_segment, target_segment, segmentation):
        '''
        Reinserts markup based on the source segment and information about phrase segmentation.
        @param source_segment the original segment in the source language
            before XML markup was removed, but after markup-aware tokenization
        @param target_segment a translated segment without markup
        @param segmentation phrase segmentation reported by Moses, a dictionary
            where keys are tuples of source spans
        '''
        source_tokens = tokenize_keep_markup(source_segment)
        target_tokens = target_segment.split(" ")
        output_tokens = []

        # gather info from segmentation
        target_phrases = []

        for source, target in segmentation.items():
    
            source_start, source_end = source[0], source[1]
            target_start, target_end = target[0], target[1]
    
            tokens_in_source_phrase = source_tokens[source_start:source_end+1]
            tokens_in_target_phrase = target_tokens[target_start:target_end+1]
    
            target_phrases.append(
                (source, target, tokens_in_source_phrase, tokens_in_target_phrase)
            )

        # gather info from source segment
        opening_elements_by_position, closing_elements_by_position = _tag_indexes_from_tokens_segmentation(source_tokens)
        
        # then for each target phrase
        for source, target, tokens_in_source, tokens_in_target in sorted(target_phrases, key=lambda x: x[1]):
            relevant_source_indexes = _indexes_from_segmentation(source)
    
            open_now = []
            close_now = []
    
            for index in relevant_source_indexes:
                # check if elements need to be opened here
                if index in opening_elements_by_position:
                    open_now.extend(opening_elements_by_position[index])
                    del opening_elements_by_position[index]
                # check if elements need to be closed here
                if index in closing_elements_by_position:
                    close_now.extend(closing_elements_by_position[index])
                    del closing_elements_by_position[index]
    
            # actually open elements
            output_tokens.extend(open_now)
            # output actual phrase
            output_tokens.extend(tokens_in_target)
            # actually close elements
            output_tokens.extend(close_now)

        if self._force_all:
            # if there are remaining opening tags
            if opening_elements_by_position:
                for key in sorted(opening_elements_by_position.keys()):
                    output_tokens.extend(opening_elements_by_position[key])

            # if there are remaining closing tags
            if closing_elements_by_position:
                for key in sorted(closing_elements_by_position.keys()):
                    output_tokens.extend(closing_elements_by_position[key])

        return " ".join(output_tokens)

    def _reinsert_markup_alignment(self, source_segment, target_segment, alignment):
        '''
        Reinserts markup based on the source segment and information about word alignment.
        @param source_segment the original segment in the source language
            before XML markup was removed, but after markup-aware tokenization
        @param target_segment a translated segment without markup
        @param alignment word alignment information reported by Moses, a
            dictionary where source tokens are keys
        '''
        output_tokens = []

        source_tokens = tokenize_keep_markup(source_segment)
        target_tokens = target_segment.split(" ")

        # gather info from source segment
        elements_by_position = _tag_indexes_from_tokens(source_tokens)

        # gather info from word alignment
        target_to_source_alignment = {}
        for source, targets in alignment.items():
            for target in targets:
                target_to_source_alignment[target] = source

        # then for each word in target
        for target_index, target_token in enumerate(target_tokens):
    
            insert_now = []
            try:
                source_index = target_to_source_alignment[target_index]
            except KeyError:
                # no alignment to the source
                source_index = None

            if source_index is not None:
                # check if elements need to be inserted here
                if source_index in elements_by_position:
                    insert_now.extend(elements_by_position[source_index])
                    del elements_by_position[source_index]

            # actually open elements
            output_tokens.extend(insert_now)
            # output actual token
            output_tokens.append(target_token)

        # elements in the last position?
        last_index = len(target_tokens)
        if last_index in elements_by_position:
            output_tokens.extend(elements_by_position[last_index])
            del elements_by_position[last_index]

        if self._force_all:
            # if there are remaining tags
            if elements_by_position:
                for key in sorted(elements_by_position.keys()):
                    output_tokens.extend(elements_by_position[key])
        return " ".join(output_tokens)

    def reinsert_markup(self, source_segment, target_segment, segmentation, alignment):
        '''
        Reinserts markup found in the source segment into the target segment.
        '''
        if self._reinsertion_strategy == REINSERTION_FULL:
            return self._reinsert_markup_full(
                source_segment,
                target_segment,
                segmentation,
                alignment
            )
        elif self._reinsertion_strategy == REINSERTION_SEGMENTATION:
            return self._reinsert_markup_segmentation(
                source_segment,
                target_segment,
                segmentation
            )
        elif self._reinsertion_strategy == REINSERTION_ALIGNMENT:
            return self._reinsert_markup_alignment(
                source_segment,
                target_segment,
                alignment
            )
        else:
            raise NotImplementedError(
                "Reinsertion strategy '%s' is unknown." % self._reinsertion_strategy
                )

def _is_opening_tag(token):
    '''
    Determines whether @param token is the opening tag of an XML element.
    '''
    return bool( re.match(r'<[a-zA-Z_][^<>\/]*(".*")?[^\/<>]*>', token) )

def _is_closing_tag(token):
    '''
    Determines whether @param token is the closing tag of an XML element.
    '''
    return bool( re.match(r"<\/[a-zA-Z_][^\/<> ]* *>", token) )

def _is_selfclosing_tag(token):
    '''
    Determines whether @param token is a self-closing XML element.
    '''
    return bool( re.match(r"<[a-zA-Z_][^\/<>]*\/>", token) )

def is_xml_tag(token):
    '''
    Determines whether @param token is an XML element tag.
    '''
    if _is_opening_tag(token) or _is_closing_tag(token) or _is_selfclosing_tag(token):
        return True
    else:
        return False

def _is_xml_comment(token):
    '''
    Determines whether @param token is an XML comment.
    '''
    return bool( re.match(r"<!\-\-[^<>]*\-\->", token) )

def _tag_in_list(tokens):
    '''
    Returns True if any token in the list is a tag.
    '''
    for token in tokens:
        if _is_opening_tag(token) or _is_closing_tag(token) or _is_selfclosing_tag(token):
            return True
    return False

def _element_names_identical(opening_tag, closing_tag):
    '''
    Attempts to parse the concatenation of two input strings.
    @return true if the element names are identical.
    '''
    # concatenate strings, if XML parser does not fail then the element names were identical
    try:
        etree.fromstring(opening_tag + closing_tag)
        return True
    except:
        # not well-formed XML = element names are not identical
        return False

def _indexes_from_segmentation(tuple):
    '''
    Lists indexes that are bounded by the start and end index
        in @param tuple.
    '''
    return list(range(tuple[0], tuple[1]+1))

def _tag_indexes_from_tokens(source_tokens):
    '''
    Identifies tokens that are tags and lists their indexes in the source
        segment.
    @param source_tokens a list of tokens that might contain tags
    '''
    elements_by_position = defaultdict(list)

    tags_seen_offset = 0

    for source_index, source_token in enumerate(source_tokens):
        if re.match("<[^<>]+>", source_token):
            elements_by_position[source_index - tags_seen_offset].append(source_token)
            tags_seen_offset += 1
        # else: do nothing

    return elements_by_position

def _tag_indexes_from_tokens_segmentation(source_tokens):
    '''
    Identifies tokens that are tags and lists their indexes in the source
        segment.
    @param source_tokens a list of tokens that might contain tags
    '''
    opening_elements_by_position = defaultdict(list)
    closing_elements_by_position = defaultdict(list)

    tags_seen_offset = 0

    for source_index, source_token in enumerate(source_tokens):
        if _is_opening_tag(source_token) or _is_selfclosing_tag(source_token):
            opening_elements_by_position[source_index - tags_seen_offset].append(source_token)
            tags_seen_offset += 1
        elif _is_closing_tag(source_token):
            closing_elements_by_position[source_index - tags_seen_offset - 1].append(source_token)
            tags_seen_offset += 1
        # else: do nothing

    return opening_elements_by_position, closing_elements_by_position

class _NodesToListHandler(xml.sax.ContentHandler):
    """
    Content handler for a SAX parser that transforms SAX events (callbacks)
    into a list of strings.
    This code is based on the saxutils XMLGenerator:
    https://hg.python.org/cpython/file/3.5/Lib/xml/sax/saxutils.py
    """
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self._pending_start_element = False
        self._nodes = []

    def startDocument(self):
        """
        In case the same handler instance is used for several documents,
        all instance variables are reset at the start of a document.
        """
        self._nodes = []
        self._pending_start_element = False

    def startElement(self, name, attrs):
        self._finish_pending_start_element()
        if attrs:
            attribute_string = _get_string_from_attrs(attrs)
            self._nodes.append(
                "<%s %s" % (name, attribute_string)
            )
        else:
            self._nodes.append("<%s" % name)
        self._pending_start_element = True

    def _finish_pending_start_element(self):
        if self._pending_start_element:
            self._nodes[-1] += ">"
            self._pending_start_element = False

    def endElement(self, name):
        if self._pending_start_element:
            self._nodes[-1] += "/>"
            self._pending_start_element = False
        else:
            self._nodes.append("</%s>" % name)

    def characters(self, content):
        if content:
            self._finish_pending_start_element()
            if not isinstance(content, str):
                content = str(content)
            tokens = [xml.sax.saxutils.escape(token) for token in content.split(" ")]
            self._nodes.extend(tokens)

    def ignorableWhitespace(self, whitespace):
        pass
        # this means that whitespace between elements cannot be transferred to the target
        # self._nodes.append(whitespace)

    def return_nodes(self):
        return [ node for node in self._nodes if node.strip() != '']

def _get_string_from_attrs(attrs):
    """
    Formats a dictionary with keys and values from parsed XML attributes
    for writing and serialization.
    """
    return " ".join(
        ['%s=%s' % (key, xml.sax.saxutils.quoteattr(value)) for key, value in attrs.items()]
    )

def tokenize_keep_markup(string):
    """
    Splits a string into a list of tokens, but do not split at whitespace if the space
    is inside an XML element tag.
    """
    handler = _NodesToListHandler()
    wrapped_string = "<root>" + string + "</root>"

    xml.sax.parseString(wrapped_string, handler)
    return handler.return_nodes()[1:-1]
