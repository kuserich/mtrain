#!/usr/bin/env python3

'''
Stores the constants needed to execute commands.
'''

import logging
import os
import re
from collections import OrderedDict

# Paths to 3rd party packages
MOSES_HOME = os.environ.get('MOSES_HOME') if os.environ.get('MOSES_HOME') else '' # Moses base directory
MOSES_BIN = MOSES_HOME + os.sep + 'bin'
FASTALIGN_HOME = os.environ.get('FASTALIGN_HOME') if os.environ.get('FASTALIGN_HOME') else '' # directory storing the fast_align binaries (fast_align, atools)
MULTEVAL_HOME = os.environ.get('MULTEVAL_HOME') if os.environ.get('MULTEVAL_HOME') else '' # MultEval base directory

# Paths to Moses files/scripts
MOSES = MOSES_HOME + os.sep + 'bin/moses'
MOSES_TRAIN_MODEL = MOSES_HOME + os.sep + 'scripts/training/train-model.perl'
MOSES_TOKENIZER = MOSES_HOME + os.sep + 'scripts/tokenizer/tokenizer.perl'
MOSES_DETOKENIZER = MOSES_HOME + os.sep + 'scripts/tokenizer/detokenizer.perl'
MOSES_TRUECASER = MOSES_HOME + os.sep + 'scripts/recaser/truecase.perl'
MOSES_TRAIN_TRUECASER = MOSES_HOME + os.sep + 'scripts/recaser/train-truecaser.perl'
MOSES_RECASER = ''
MOSES_TRAIN_RECASER = MOSES_HOME + os.sep + 'scripts/recaser/train-recaser.perl'
MOSES_MERT = MOSES_HOME + os.sep + 'scripts/training/mert-moses.pl'
MOSES_COMPRESS_PHRASE_TABLE = MOSES_HOME + os.sep + 'bin/processPhraseTableMin'
MOSES_COMPRESS_REORDERING_TABLE = MOSES_HOME + os.sep + 'bin/processLexicalTableMin'

# Paths to KenLM files/scripts (included in Moses)
KENLM_TRAIN_MODEL = MOSES_HOME + os.sep + 'bin/lmplz'
KENLM_BUILD_BINARY = MOSES_HOME + os.sep + '/bin/build_binary'

# Paths to fast_align files/scripts
FAST_ALIGN = FASTALIGN_HOME + os.sep + 'fast_align'
ATOOLS = FASTALIGN_HOME + os.sep + 'atools'

# Path to multeval script
MULTEVAL = MULTEVAL_HOME + os.sep + 'multeval.sh'

# Characters with special meanings in Moses
# Replacement is ordered: First char listed here is replaced first, etc.
MOSES_SPECIAL_CHARS = OrderedDict()
MOSES_SPECIAL_CHARS["&"] = "&amp;"
MOSES_SPECIAL_CHARS["|"] = "&#124;"
MOSES_SPECIAL_CHARS["<"] = "&lt;"
MOSES_SPECIAL_CHARS[">"] = "&gt;"
MOSES_SPECIAL_CHARS['"'] = "&quot;"
MOSES_SPECIAL_CHARS["'"] = "&apos;"
MOSES_SPECIAL_CHARS["["] = "&#91;"
MOSES_SPECIAL_CHARS["]"] = "&#93;"

# Protected patterns relevant for tokenization and masking
# Dictionary[mask token] = 'regular expression'
PROTECTED_PATTERNS_FILE_NAME = 'protected-patterns.dat'
PROTECTED_PATTERNS = {}
PROTECTED_PATTERNS['xml'] = r'<\/?[a-zA-Z_][a-zA-Z_.\-0-9]*[^<>]*\/?>'
PROTECTED_PATTERNS['email'] = r'[\w\-\_\.]+\@([\w\-\_]+\.)+[a-zA-Z]{2,}'
PROTECTED_PATTERNS['url'] = r'(https?:\/\/(?:www\.|(?!www))[^\s\.]+\.[^\s]{2,}|www\.[^\s]+\.[^\s]{2,})'

# Relative paths to components inside working directory
PATH_COMPONENT = {
    # Maps components to their base directory name
    "corpus": "corpus",
    "engine": "engine",
    "evaluation": "evaluation",
    "logs": "logs"
}

# Default file names and affixes
BASENAME_TRAINING_CORPUS = 'train'
BASENAME_TUNING_CORPUS = 'tune'
BASENAME_EVALUATION_CORPUS = 'test'
SUFFIX_TOKENIZED = 'tokenized'
SUFFIX_MASKED = 'masked'
SUFFIX_CLEANED = 'cleaned'
SUFFIX_LOWERCASED = 'lowercased'
SUFFIX_TRUECASED = 'truecased'
SUFFIX_FINAL = 'final'

# Valid language codes for Moses tokenizer
MOSES_TOKENIZER_LANG_CODES = {
    "ca": "Catalan",
    "cs": "Czech",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "ga": "Irish",
    "hu": "Hungarian",
    "is": "Icelandic",
    "it": "Italian",
    "lv": "Latvian",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sv": "Swedish",
    "ta": "Tamil",
}

# Valid language codes for METEOR 1.4 (used by MultEval)
METEOR_LANG_CODES = {
    # fully supported:
    "en": "English",
    "ar": "Arabic",
    "cz": "Czech",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    # only partially supported:
    "da": "Danish",
    "fi": "Finnish",
    "hu": "Hungarian",
    "it": "Italian",
    "nl": "Dutch",
    "no": "Norwegian",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "se": "Swedish",
    "tr": "Turkish"
}

# Valid casing strategies
SELFCASING = "selfcasing"
TRUECASING = "truecasing"
RECASING = "recasing"
CASING_STRATEGIES = {
    SELFCASING: "the decoder is trained on lowercased input and cased output",
    TRUECASING: "the decoder is trained on truecased input and output " +
        "(trains a separate truecasing model)",
    RECASING: "the decoder is trained on lowercased input and output " +
        "(trains a separate recasing model)"
}

# Masking
MASKING = "masking"
# Valid masking strategies
MASKING_ALIGNMENT = 'alignment'
MASKING_IDENTITY = "identity"
MASKING_STRATEGIES = {
    MASKING_ALIGNMENT: "mask tokens are not unique, content is restored based on " +
        "the source segment and word alignment",
    MASKING_IDENTITY: "all mask tokens in a segment have unique IDs, content " +
        "is restored based solely on mapping information",
}
# More fine-grained defaults for masking
FORCE_MASK_TRANSLATION = False # constraint decoding for the mask token

# Markup reinsertion
REINSERTION = 'reinsertion'
# Valid reinsertion strategies
REINSERTION_FULL = 'full'
REINSERTION_SEGMENTATION = 'segmentation'
REINSERTION_ALIGNMENT = 'alignment'
REINSERTION_STRATEGIES = {
    REINSERTION_FULL: "reinsert markup with a hybrid method that uses both " +
        "phrase segmentation and alignment information",
    REINSERTION_SEGMENTATION: "reinsert markup based solely on information " +
        "about phrase segmentation",
    REINSERTION_ALIGNMENT: "reinsert markup based solely on information " +
        "about word alignments"
}
# More fine-grained defaults for reinsertion
FORCE_REINSERT_ALL = False # whether unplaceable markup should be inserted anyway

# XML processing
XML_PASS_THROUGH = 'pass-through'
XML_STRIP = 'strip' # for training
XML_STRIP_REINSERT = 'strip-reinsert' # for translation
XML_MASK = 'mask'
# Valid strategies for training
XML_STRATEGIES_TRAINING = {
    XML_PASS_THROUGH: "do nothing, except for properly escaping special " +
        "characters before training the models (not recommended if your " +
        "input contains markup)",
    XML_STRIP: "remove markup from all segments before training, and do " +
        "not store the markup anywhere",
    XML_MASK: "replace stretches of markup with mask tokens before " +
        "training. Then train the models with segments that contain " +
        "mask tokens"
}
# valid strategies for translation
XML_STRATEGIES_TRANSLATION = {
    XML_PASS_THROUGH: "do nothing, except for properly escaping special " +
        "characters before translation and undoing this afterwards " +
        "(not recommended if your input contains markup)",
    XML_STRIP: "remove markup from all input segments before translation " +
        "and do not reinsert afterwards",
    XML_STRIP_REINSERT: "remove markup from all segments before translation " +
        "and reinsert into the translated segment afterwards",
    XML_MASK: "replace stretches of markup with mask tokens before " +
        "translation. After translation, reverse this process, replace " +
        "the mask tokens with the original content"
}
# More fine-grained defaults for XML processing
XML_STRATEGIES_DEFAULTS = {
    XML_STRIP: REINSERTION_ALIGNMENT,
    XML_STRIP_REINSERT: REINSERTION_ALIGNMENT,
    XML_MASK: MASKING_IDENTITY
}

# Python logging levels
LOGGING_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
