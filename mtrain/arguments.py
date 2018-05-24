#!/usr/bin/env python3

import os
import sys
import logging
import argparse

from mtrain import constants as C
from mtrain import checker

"""
Defines command line arguments.
"""


def add_required_arguments(parser):
    """
    Adds positional arguments.
    """
    parser.add_argument(
        "basepath",
        type=str,
        help="common path/file prefix of the training corpus' source and " +
        "target side, e.g., `/foo/bar/training_corpus`"
    )
    parser.add_argument(
        "src_lang",
        type=str,
        help="source language code: valid choices are `" +
             "`, `".join([lang for lang in sorted(C.MOSES_TOKENIZER_LANG_CODES.keys())]) +
             "`",
        choices=C.MOSES_TOKENIZER_LANG_CODES.keys(),
        metavar='src_lang'  # overrides ugly double-listing of available choices in '--help'
    )
    parser.add_argument(
        "trg_lang",
        type=str,
        help="target language code: same valid choices as in src_lang",
        choices=C.MOSES_TOKENIZER_LANG_CODES.keys(),
        metavar='trg_lang'  # overrides ugly double-listing of available choices in '--help'
    )


def add_backend_arguments(parser):
    """
    """
    parser.add_argument(
        "--backend",
        type=str,
        help="decide which backend is to be used as training engine." +
             " Valid choices are: " +
             "; ".join(["`%s`: %s" % (name, descr) for name, descr in C.BACKEND_CHOICES.items()]),
        choices=C.BACKEND_CHOICES.keys(),
        default=C.BACKEND_MOSES
    )
    parser.add_argument(
        "--threads",
        type=int,
        help="the number of threads to be used at most, default=`8`",
        default=8
    )


def add_io_arguments(parser):
    """
    Adds arguments related to files and paths.
    """
    parser.add_argument(
        "-o", "--output_dir",
        type=str,
        help="target directory for all output. The curent working directory " +
             "($PWD) is used by default.",
        default=os.getcwd()
    )
    parser.add_argument(
        "--temp_dir",
        help="directory for temporary files created during trainig, default=`/tmp`",
        default="/tmp"
    )
    parser.add_argument(
        "--logging",
        help="logging level in STDERR, default=`INFO`",
        choices=C.LOGGING_LEVELS.keys(),
        default="INFO"
    )


def add_moses_arguments(parser):
    """
    Adds arguments specific to Moses.
    """
    moses_args = parser.add_argument_group("Moses arguments")

    moses_args.add_argument(
        "-n", "--n_gram_order",
        type=int,
        help="the language model's n-gram order, default=`5`",
        default=5
    )
    moses_args.add_argument(
        "--keep_uncompressed_models",
        help="do not delete uncompressed models created during training",
        action='store_true'
    )


def add_preprocessing_arguments(parser):
    """
    """
    parser.add_argument(
        "--min_tokens",
        type=int,
        help="the minimum number of tokens per segments; segments with less " +
             "tokens will be discarded, default=`1`",
        default=1
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        help="the maximum number of tokens per segments; segments with more " +
             "tokens will be discarded, default=`80`",
        default=80
    )
    parser.add_argument(
        "-c", "--caser",
        type=str,
        help="casing strategy: " +
             "; ".join(["`%s`: %s" % (name, descr) for name, descr in C.CASING_STRATEGIES.items()]),
        choices=C.CASING_STRATEGIES.keys(),
        default=C.TRUECASING
    )
    parser.add_argument(
        "-t", "--tune",
        help="enable tuning. If an integer is provided, the given number of " +
             "segments will be randomly taken from the training corpus " +
             "(basepath). Alternatively, the basepath to a separate tuning " +
             "corpus can be provided. Examples: `2000`, `/foo/bar/tuning_corpus`"
    )
    parser.add_argument(
        "--preprocess_external_tune",
        help="preprocess external tuning corpus. Don't use if " +
             "the external files provided in '--tune' are already preprocessed.",
        default=False,
        action='store_true'
    )
    parser.add_argument(
        "--masking",
        help="enable masking. Valid strategies are: " +
             "; ".join(["`%s`: %s" % (name, descr) for name, descr in C.MASKING_STRATEGIES.items()]),
        choices=C.MASKING_STRATEGIES.keys(),
        default=None
    )
    parser.add_argument(
        "--xml_input",
        type=str,
        help="decide how XML fragments in the input segments should " +
             "be dealt with. Valid choices are: " +
             "; ".join(["`%s`: %s" % (name, descr) for name, descr in C.XML_STRATEGIES.items()]),
        choices=C.XML_STRATEGIES.keys(),
        default=None
    )


def add_eval_arguments(parser):
    """
    """
    parser.add_argument(
        "-e", "--eval",
        help="enable evaluation. If an integer is provided, the given number " +
             "of segments will be randomly taken from the training corpus " +
             "(basepath). Alternatively, the basepath to a separate evaluation " +
             "corpus can be provided. Examples: `2000`, `/foo/bar/eval_corpus`"
    )
    parser.add_argument(
        "--eval_lowercase",
        help="lowercase reference and translation before evaluation. Otherwise," +
             "evaluation uses the engine's casing strategy.",
        default=False,
        action='store_true'
    )
    parser.add_argument(
        "--extended_eval",
        action="store_true",
        help="perform multiple evaluations that vary the appearance of the test files: " +
             "lowercased or not, detokenized or not, with markup or without.",
        default=False
    )


def add_nematus_arguments(parser):
    """
    Adds arguments specific to Nematus.
    """
    nematus_args = parser.add_argument_group("Nematus arguments")

    nematus_args.add_argument(
        "--bpe_ops",
        type=int,
        help="decide how many byte-pair operations are to be performed when learning the " +
        "byte-pair encoding model with nematus backend, default=`89500` operations",
        default=C.BPE_NUM_JOINT_OPERATIONS
    )
    nematus_args.add_argument(
        "--device_train",
        type=str,
        help="A GPU or CPU device for training.",
        default=C.TRAIN_DEVICE
    )
    nematus_args.add_argument(
        "--preallocate_train",
        type=str,
        help="Preallocate memory on a GPU device for training.",
        default=C.TRAIN_PREALLOCATE
    )
    nematus_args.add_argument(
        "--device_validate",
        type=str,
        help="A GPU or CPu device for validation." +
             "Omit if '--external_validation_script' is provided.",
        default=C.VALIDATE_DEVICE
    )
    nematus_args.add_argument(
        "--preallocate_validate",
        type=str,
        help="Preallocate memory on a GPU device for validation.",
        default=C.VALIDATE_PREALLOCATE
    )
    nematus_args.add_argument(
        "--validation_freq",
        type=int,
        help="Perform validation of the model after X updates.",
        default=C.VALIDATION_FREQ
    )
    nematus_args.add_argument(
        "--external_validation_script",
        type=str,
        help="Optional path to external validation script that is called during " +
             "training of nematus engine. Do not use if you want mtrain to manage external validation.",
        default=None
    )
    nematus_args.add_argument(
        "--max_epochs",
        type=int,
        help="Maximum number of epochs for training.",
        default=C.MAX_EPOCHS
    )
    nematus_args.add_argument(
        "--max_updates",
        type=int,
        help="Maximum number of updates to the model.",
        default=C.MAX_UPDATES
    )


def get_training_parser():
    parser = argparse.ArgumentParser()
    parser.description = ("Trains either an SMT system with Moses " +
                          "or an NMT system with Nematus.")

    add_required_arguments(parser)
    add_backend_arguments(parser)
    add_io_arguments(parser)
    add_preprocessing_arguments(parser)
    add_eval_arguments(parser)

    # options specific to a backend
    add_moses_arguments(parser)
    add_nematus_arguments(parser)

    return parser


def check_environment(args):
    '''
    Abort if environment variables specific for chosen backend are not set.

    Note: 'MULTEVAL_HOME' ist specific for evaluation and thus,
    checked only if evaluation chosen.
    '''
    checker.check_environment_variable(C.MOSES_HOME, 'MOSES_HOME', 'moses')

    if args.backend == C.BACKEND_MOSES:
        checker.check_environment_variable(C.FASTALIGN_HOME, 'FASTALIGN_HOME', 'fast_align')
    else:
        checker.check_environment_variable(C.NEMATUS_HOME, 'NEMATUS_HOME', 'nematus')
        checker.check_environment_variable(C.SUBWORD_NMT_HOME, 'SUBWORD_NMT_HOME', 'subword-nmt')

    if args.eval:
        checker.check_environment_variable(C.MULTEVAL_HOME, 'MULTEVAL_HOME', 'multeval.sh')


def check_arguments_moses(args):
    '''
    Check for arguments if fit for moses, either combination or specific argument may
    be not (yet) applicable for the backend. Depending on severity, user is warned and maybe
    program terminated.

    @param args all arguments passed from 'get_argument_parser()'
    '''
    # generic masking and XML masking currently not possible at the same time for backend moses
    if args.masking and args.xml_input == C.XML_MASK:
        logging.critical("Invalid command line options. For backend %s, " +
                         "choose either '--masking' or '--xml_input mask', but not both. " +
                         "See '-h'/'--help' for more information.", C.BACKEND_MOSES)
        sys.exit()


def check_arguments_nematus(args):
    '''
    Check for arguments if fit for nematus, either combination or specific argument may
    be not (yet) applicable for the backend. Depending on severity, user is warned and maybe
    program terminated.

    @param args all arguments passed from 'get_argument_parser()'
    '''
    pass


def check_arguments(args):
    """
    """
    if args.backend == C.BACKEND_MOSES:
        check_arguments_moses(args)
    else:
        check_arguments_nematus(args)
