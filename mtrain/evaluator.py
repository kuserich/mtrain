#!/usr/bin/env python3
'''
Automatic evaluation of a trained engine, based on the translations of an evaluation set
'''

import os
import re
import logging
import itertools

from mtrain.constants import *
from mtrain import assertions
from mtrain import commander
from mtrain.translation import TranslationEngineBase, TranslationEngineMoses # todo import and implement TranslationEngineNematus when necessary
from mtrain.preprocessing import cleaner
from mtrain.preprocessing import lowercaser
from mtrain.preprocessing.reinsertion import tokenize_keep_markup
from mtrain.preprocessing.tokenizer import Tokenizer, Detokenizer
from mtrain.preprocessing.xmlprocessor import XmlProcessor

class Evaluator(object):
    '''
    Translates a set of test sentences and evaluates the translations with automatic
    metrics of translation quality.
    '''
    def __init__(self, basepath, eval_corpus_path, src_lang, trg_lang, xml_strategy,
        num_threads, eval_tool=MULTEVAL_TOOL, tokenizer_trg=None, xml_processor=None,
        extended_eval=False):
        '''
        Creates an evaluation directory, translates test sentences and scores them.
        @param basepath a directory containing a trained engine
        @param eval_corpus_path path to the evaluation corpus
        @param src_lang the language code of the source language, e.g., `en`
        @param trg_lang the language code of the target language, e.g., `fr`
        @param xml_strategy whether fragments of markup in the data should be
            passed through, removed or masked
        @param num_threads max number of threads to be used by all processed
            invoked during evaluation
        @param eval_tool an external tool used for evaluation
        @param tokenizer_trg the target language tokenizer used for the training corpus
        @param xml_processor the XML processor used for the training corpus
        @param extended_eval perform multiple evaluations that vary processing
            steps applied to the test set before each round of evaluation
        '''
        # file paths and languages
        self._basepath = basepath
        self._eval_corpus_path = eval_corpus_path
        self._src_lang = src_lang
        self._trg_lang = trg_lang
        # strategies
        self._xml_strategy = xml_strategy
        # evaluation options
        self._num_threads = num_threads
        self._eval_tool = eval_tool
        self._extended_eval = extended_eval
        self._num_rounds = 0
        self._translations = []
        # processors for target side of evaluation corpus
        self._xml_processor = xml_processor if xml_processor else XmlProcessor(self._xml_strategy)
        self._tokenizer = tokenizer_trg
        self._detokenizer = Detokenizer(self._trg_lang, uppercase_first_letter=False)

        # create target directories
        self._base_dir_evaluation = os.path.sep.join([self._basepath, PATH_COMPONENT['evaluation']])
        if not assertions.dir_exists(self._base_dir_evaluation):
            os.mkdir(self._base_dir_evaluation)
        if self._eval_tool == MULTEVAL_TOOL:
            self._base_dir_multeval = self._base_dir_evaluation + os.sep + MULTEVAL_TOOL.lower()
            if not assertions.dir_exists(self._base_dir_multeval):
                os.mkdir(self._base_dir_multeval)
        else:
            # currently, tools other than MultEval are not supported
            raise NotImplementedError

    def _preprocess_eval_corpus_trg(self):
        '''
        Opens the target side of the reference corpus and applies selected
        processing steps identical to the postprocessing steps of machine-
        translated segments.
        '''
        path_eval_trg = self._get_path_eval(self._trg_lang)
        path_eval_trg_processed = self._get_path_eval_trg_processed()
        with open(path_eval_trg, 'r') as path_eval_trg:
            with open(path_eval_trg_processed, 'w') as path_eval_trg_processed:
                for target_segment in path_eval_trg:
                    target_segment = target_segment.strip()
                    if self._strip_markup_eval:
                        target_segment = self._xml_processor._strip_markup(target_segment)
                    if self._lowercase_eval:
                        target_segment = lowercaser.lowercase_string(target_segment)
                    if not self._detokenize_eval:
                        target_segment = self._tokenizer.tokenize(target_segment, split=False)
                        # markup-aware tokenizer does not escape, but un-detokenized machine translation
                        # is escaped, except for markup; do the same here
                        if self._xml_strategy:
                            target_segment = self._escape_if_not_markup(target_segment)
                        # else, the tokenizer already escapes properly
                    path_eval_trg_processed.write(target_segment + "\n")

    def _escape_if_not_markup(self, segment):
        '''
        Splits a segment into tokens (markup-aware) and escapes tokens
        if they are not markup tags.
        '''
        escaped_tokens = []
        tokens = []
        for token in re.split("(<[^<>]+>)", segment):
            if re.match("<[^<>]+>", token):
                # markup, do not escape
                escaped_tokens.append(token)
            elif token:
                escaped_tokens.append(cleaner.escape_special_chars(token.strip()))
        return " ".join(escaped_tokens)

    def _translate_eval_corpus_src(self):
        '''
        Translates sentences from an evaluation corpus.

        # todo import and implement TranslationEngineNematus when necessary,
        #   make @abc.abstractmethod and separate this implementation from nematus backend
        '''
        self._engine = TranslationEngineMoses(
            self._basepath,
            self._src_lang,
            self._trg_lang,
            uppercase_first_letter=False,
            xml_strategy=self._xml_strategy,
            quiet=self._extended_eval
        )
        # determine path to source side of evaluation corpus
        corpus_eval_src = self._get_path_eval(self._src_lang)

        logging.info("Translating evaluation corpus")
        # translate eval corpus
        with open(corpus_eval_src, 'r') as corpus_eval_src:
            for source_segment in corpus_eval_src:
                target_segment = self._engine.translate(
                    source_segment,
                    preprocess=True,
                    lowercase=False,
                    detokenize=False
                )
                self._translations.append(target_segment)

        # remove all engine processes
        self._engine.close()

    def _postprocess_translations(self):
        '''
        Postprocesses existing translations and writes them to file.
        '''
        # determine path to hypothesis file
        hypothesis_path = self._get_path_hypothesis()
        with open(hypothesis_path, 'w') as hypothesis:
            for target_segment in self._translations:
                if self._strip_markup_eval:
                    target_segment = self._xml_processor._strip_markup(target_segment)
                if self._lowercase_eval:
                    target_segment = lowercaser.lowercase_string(target_segment)
                if self._detokenize_eval:
                    target_segment = self._detokenizer.detokenize(target_segment.split(" "))
                hypothesis.write(target_segment + "\n")

    def _get_path_eval(self, lang):
        '''
        Returns the path to a side of the reference corpus.
        @param lang language of the source or target side
        '''
        return self._eval_corpus_path + os.sep + '.'.join([BASENAME_EVALUATION_CORPUS, lang])

    def _get_path_eval_trg_processed(self):
        '''
        Returns the path to the target side of the reference corpus, where specific
            processing steps were applied for evaluation.
        '''
        return self._base_dir_multeval + os.sep + 'reference' + "." + ".".join(self._eval_options) + "." + self._trg_lang

    def _get_path_hypothesis(self):
        '''
        Returns the path to the file translated by the engine.
        '''
        return self._base_dir_multeval + os.sep + "hypothesis" + "." + ".".join(self._eval_options) + "." + self._trg_lang 

    def _get_path_eval_output(self):
        '''
        Returns the path to where the evaluation results should be stored.
        '''
        return self._base_dir_multeval + os.sep + "hypothesis" + "." + ".".join(self._eval_options) + "." + self._eval_tool.lower()

    def _score(self):
        '''
        Scores existing translations with an external tool.
        '''
        # determine paths to relevant files
        output_path = self._get_path_eval_output()
        hypothesis_path = self._get_path_hypothesis()
        corpus_evaluation_trg = self._get_path_eval_trg_processed()

        if self._eval_tool == MULTEVAL_TOOL:
            self._multeval(output_path, hypothesis_path, corpus_evaluation_trg)
        else:
            raise NotImplementedError

    def _multeval(self, output_path, hypothesis_path, corpus_evaluation_trg):
        '''
        Scores existing translations with MultEval.
        @param output_path path to file where results should be stored
        @param hypothesis_path path to machine translated segments
        @param corpus_evaluation_trg path to target side of reference corpus
        '''
        # determine whether METEOR scores can be computed
        meteor_argument = '--meteor.language "%s"' % self._trg_lang
        if self._trg_lang not in METEOR_LANG_CODES.keys():
            logging.warning("Target language not supported by METEOR library. Evaluation will not include METEOR scores.")
            meteor_argument = '--metrics bleu,ter,length'

        multeval_command = '{script} eval --verbosity 0 --bleu.verbosity 0 --threads "{num_threads}" {meteor_argument} --refs "{corpus_evaluation_trg}" --hyps-baseline "{hypothesis}" > "{output_path}"'.format(
            script=MULTEVAL,
            num_threads=self._num_threads,
            meteor_argument=meteor_argument,
            corpus_evaluation_trg=corpus_evaluation_trg,
            hypothesis=hypothesis_path,
            output_path=output_path
        )
        commander.run(
            multeval_command,
            "Evaluating with MultEval" if not self._extended_eval else None 
        )

    def _eval_round(self, lowercase, detokenize, strip_markup):
        '''
        One round of evaluation. Precondition: source side of the evaluation
        corpus has been translated already.
        @param lowercase whether to lowercase all segments before evaluation
        @param detokenize whether to detokenize all segments before evaluation
        @param strip_markup whether all markup should be removed before evaluation
        '''
        # reset evaluation options for each round
        self._lowercase_eval = lowercase
        self._detokenize_eval = detokenize
        self._strip_markup_eval = strip_markup
        # collect options and log them
        self._collect_evaluation_options()
        self._log_evaluation_options()        
        # preprocess target side of evaluation corpus (reference) to match the processing
        #     applied to the translations (hypothesis) and write reference to file
        self._preprocess_eval_corpus_trg()
        # postprocess translations (hypothesis) and write to file
        self._postprocess_translations()
        # score the current pair of reference and translations files
        self._score()

    def _eval_rounds(self):
        '''
        Coordinates 1 to n rounds of evaluation. Each round preprocesses the
        reference, postprocesses the hypothesis, writes both to file and
        scores them.
        '''
        if self._extended_eval:
            permutations = list(itertools.product([True, False], repeat=3))
            for permutation in permutations:
                self._eval_round(*permutation)
        else:
            self._eval_round(
                lowercase=self._lowercase_eval,
                detokenize=self._detokenize_eval,
                strip_markup=self._strip_markup_eval
            )
    def _collect_evaluation_options(self):
        '''
        Collects the current evaluation options. Options
        may differ between different round of evaluation.
        '''
        self._eval_options = []
        if self._lowercase_eval:
            self._eval_options.append(SUFFIX_LOWERCASED)
        else:
            self._eval_options.append(SUFFIX_CASED)
        if self._detokenize_eval:
            self._eval_options.append(SUFFIX_DETOKENIZED)
        else:
            self._eval_options.append(SUFFIX_TOKENIZED)
        # todo: only if there is a self._xml_strategy?
        if self._strip_markup_eval:
            self._eval_options.append(SUFFIX_WITHOUT_MARKUP)
        else:
            self._eval_options.append(SUFFIX_WITH_MARKUP)

    def _log_evaluation_options(self):
        '''
        Logs evaluation options with the appropriate level.
        '''
        display_options = [item.replace("_", " ") for item in self._eval_options]
        message = "Evaluation options: "
        if self._extended_eval:
            self._num_rounds += 1
            message = "Extended evaluation round %i, options: " % self._num_rounds
        logging.info(
            message + ', '.join(display_options[:-1]) + ' and ' + display_options[-1]
        )

    # only exposed method
    def evaluate(self, lowercase, detokenize, strip_markup):
        '''
        Translates test segment and scores them with an external tool, saves
            results to a file.
        @param lowercase whether to lowercase all segments before evaluation
        @param detokenize whether to detokenize all segments before evaluation
        @param strip_markup whether all markup should be removed before evaluation

        Note: tokenized evaluation implies escaped evaluation, detokenized
            evaluation implies deescaped evaluation
        '''
        logging.info("Evaluating trained engine")
        # set object attributes
        self._lowercase_eval = lowercase
        self._detokenize_eval = detokenize
        self._strip_markup_eval = strip_markup
        # perform translation once
        self._translate_eval_corpus_src()
        # possibly perform several rounds of evaluation
        self._eval_rounds()
