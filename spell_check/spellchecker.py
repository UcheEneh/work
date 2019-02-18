from __future__ import absolute_import, division, unicode_literals

import os
import json
import string
from collections import Counter

from spellchecker_utils import load_file, _parse_into_words, load_entities #,write_file,


class WordFrequency(object):
    """ 
    Store the `dictionary` as a word frequency list while allowing for
        different methods to load the data and update over time     
    """
    
    __slots__ = ["_dictionary", "_total_words", "_unique_words", "_letters"]
    
    def __init__(self):
        self._dictionary = Counter()
        self._total_words = 0
        self._unique_words = 0
        self._letters = set()
    
    # Check if word is in big dictinary
    def __contains__(self, key):
        """ turn on getitem """
        return key.lower() in self._dictionary
    
    # Return the frequency of the word if in big dictionary
    def __getitem__(self, key):
        """ turn on get item """
        return self._dictionary[key.lower()]
    
    # Remove a word from the dictionary and 'return' it
    def pop(self, key, default=None):
        # Don't think this has to be defined ... maybe because of None...
        """ Remove the key and return the associated value or default if not
            found
            Args:
                key (str): The key to remove
                default (obj): The value to return if key is not present 
        """
        return self._dictionary.pop(key.lower(), default)
    
    @property
    def dictionary(self):
        """
        Counter: A counting dictionary of all words in the corpus and the \
            number of times each has been seen
        """
        return self._dictionary
    
    # The total number of words in the dictionary
    @property
    def total_words(self):
        # int: The sum of all word occurances in the word frequency dictionary
        return self._total_words
    
    @property
    def unique_words(self):
        # int: The total number of unique words in the word frequency list
        return self._unique_words
    
    # Letters a-z (for google top 10000 words)
    @property
    def letters(self):
        # str: The listing of all letters found within the corpus
        return self._letters
    
    # Returns a word in the dictionary
    def keys(self):
        """ Iterator over the key of the dictionary
            Yields:
                str: The next key in the dictionary
            Note:
                This is the same as `spellchecker.words()` """
        for key in self._dictionary.keys():
            yield key
    
    # Returns a word in the dictionary
    def words(self):
        """ Iterator over the words in the dictionary
            Yields:
                str: The next word in the dictionary
            Note:
                This is the same as `spellchecker.keys()` """
        for word in self._dictionary.keys():
            yield word
    
    # Would probably only need this, not the proper text documents
    def load_dictionary(self, filename):
        """ Load in a pre-built word frequency list
        
            Args:
                filename (str): The filepath to the json (optionally gzipped) \
                file to be loaded
                encoding (str): The encoding of the dictionary 
        """
        #filename = "en.txt"
        with load_file(filename) as data:
            self._dictionary.update(json.loads(data)) #read in json file
            self._update_dictionary()
        
    # Would most likely not need this, except working with entity_dict
    def load_text_file(self, filename):
        """ Load in a text file from which to generate a word frequency list
        
            Args:
                filename (str): The filepath to the text file to be loaded
                encoding (str): The encoding of the text file 
        """
        with load_file(filename) as data:
            self.load_text(data)    
            
    def load_text(self, text):
        """ Load text from which to generate a word frequency list
            Args:
                text (str): The text to be loaded 
        """
        self._dictionary.update(_parse_into_words(text))
        self._update_dictionary()
        
    def load_words(self, words):
        """ Load a list of words from which to generate a word frequency list
            Args:
                words (list): The list of words to be loaded 
        """
        self._dictionary.update([word.lower() for word in words])
        self._update_dictionary()
        
    def add(self, word):
        """ Add a word to the word frequency list
            Args:
                word (str): The word to add 
        """
        self.load_words([word])
        
    def remove_words(self, words):
        """ Remove a list of words from the word frequency list
            Args:
                words (list): The list of words to remove """
        for word in words:
            self._dictionary.pop(word.lower())
        self._update_dictionary()
        
    def remove(self, word):
        """ Remove a word from the word frequency list
            Args:
                word (str): The word to remove """
        self._dictionary.pop(word.lower())
        self._update_dictionary()
    
    # Remove if word frequency isn't at least 5
    def remove_by_threshold(self, threshold=5):
        """ Remove all words at, or below, the provided threshold
            Args:
                threshold (int): The threshold at which a word is to be \
                removed 
        """
        keys = [x for x in self._dictionary.keys()]
        for key in keys:
            if self._dictionary[key] <= threshold:
                self.dictionary.pop(key)
        self._update_dictionary()
                    
    def _update_dictionary(self):
        """ Update the word frequency object """
        self._total_words = sum(self._dictionary.values())
        self._unique_words = len(self.dictionary.keys())
        self._letters = set()
        for key in self._dictionary:
            self._letters.update(key)
            


class SpellChecker(object):
    """ The SpellChecker class performs a simple spell checking algorithm. 
        
        Based on the work by
        Peter Norvig (https://norvig.com/spell-correct.html)
        
        Args:
            local_dictionary (str): The path to a locally stored word \
                frequency dictionary. If provided, no language will be loaded
            distance (int): The edit distance to use. Defaults to 2 
    """
    
    __slots__ = ["_distance", "_word_frequency"]
    
    def __init__(self, language, local_dictionary=None, distance=2):
        self._distance = None
        self.distance = distance
        self._word_frequency = WordFrequency()
        
        #######################################################
        #    Load dictionary using only english dictionary    #
        #######################################################
        if local_dictionary:    
            self._word_frequency.load_dictionary(local_dictionary)
            # Basically word_frequency contains a list of words and their frequency of 
            # appearances from the input loaded text file
        elif language:
            filename = "{}.txt".format(language.lower())
                        
            curr_path = os.path.dirname(__file__)
            #full_filename = os.path.join(here, "resources", filename)
            full_filename = '{}/resources/'.format(curr_path) + filename
            
            if not os.path.exists(full_filename):
                msg = ( "The provided dictionary language ({}) does not " "exist!" 
                        ).format(language.lower())
                raise ValueError(msg)
            self._word_frequency.load_dictionary(full_filename)
            
    # Checks if a word is in dictionary ie performs "known" check 
    def __contains__(self, key):
        return key in self._word_frequency
    
    # checks frequency of occurence of a word in dictionary ie performs  "frequency" checks
    def __getitem__(self, key):
        return self._word_frequency[key]
    
    # WordFrequency: Gives a dictionary of the (word : frequency)             
    @property
    def word_frequency(self):
        return self._word_frequency
    
    @property
    def get_distance(self):
        """ int: The maximum edit distance to calculate
            Note: Valid values are 1 or 2; if an invalid value is passed, \
                defaults to 2 
        """
        return self._distance
    
    # Set the distance param 
    @distance.setter
    def set_distance(self, val):
        tmp = 2
        try:
            int(val)
            if val > 0 and val <= 2:
                tmp = val
        except (ValueError, TypeError):
            pass
        self._distance = tmp
        
    @staticmethod
    def split_words(text):
        """ Split text into individual words using a simple whitespace regex
            Args:
                text (str): The text to split into individual words
            Returns:
                list(str): A listing of all words in the provided text 
        """
        return _parse_into_words(text)
    
    # Return the probability of the word being the replacement by comparing the frequency of occurence
    def word_probability(self, word, total_words=None):  
        """ Calculate the probability of the `word` being the desired, correct
            word
            
            Args:
                word (str): The word for which the word probability is calculated
                total_words (int): The total number of words to use in the \
                calculation; use the default for using the whole word frequency
            Returns:
                float: The probability that the word is the correct word 
        """
        if total_words is None:
            total_words = self._word_frequency.total_words
        return self._word_frequency.dictionary[word] / total_words
    
    def correction(self, word):
        """ The most probable correct spelling for the word
        
            Args:
                word (str): The word to correct
            Returns:
                str: The most likely candidate 
        """
        return max(self.candidates(word), key=self.word_probability)
    
    def candidates(self, word):
        """ Generate possible spelling corrections for the provided word up to
            an edit distance of two, only when needed
            
            Args:
                word (str): The word for which to calculate candidate spellings
            Returns:
                set: The set of words that are possible candidates 
        """
        #if word is correct already
        if self.known([word]):  
            return{word}
            
        # get edit distance 1
        res = [x for x in self.edit_distance_1(word)]
        # check if combinations in res are actual words
        tmp = self.known(res)   
        if tmp: 
            return tmp
        
        # if still not found, use edit distance 1 to calculate edit distance 2
        if self._distance == 2:
            tmp = self.known([x for x in self.__edit_distance_alt(res)])
            if tmp:
                return tmp
            return {word}
    
    # Check if word is in the big dictionary
    def known(self, words):
        """ The subset of `words` that appear in the dictionary of words
        
            Args:
                words (list): List of words to determine which are in the \
                corpus
            Returns:
                set: The set of those words from the input that are in the \
                corpus 
        """
        tmp = [w.lower() for w in words]
        
        # Return the word if it is in the dictionary or if it is something that 
        # shouldn't be checked e.g numbers
        return set(w for w in tmp
                   if w in self._word_frequency.dictionary
                   or not self._check_if_should_check(w))
        
    # Check if word not in big dictionary   
    def unknown(self, words):
        """ The subset of `words` that do not appear in the dictionary
            
            Args:
                words (list): List of words to determine which are not in the \
                corpus
            Returns:
                set: The set of those words from the input that are not in \
                the corpus 
        """
        tmp = [w.lower() for w in words if self._check_if_should_check(w)]
        # Basically returns the words that are not in the dictionary
        return set(w for w in tmp if w not in self._word_frequency.dictionary)
    
    #Perform Levenshtein edit distances
    def edit_distance_1(self, word):
        """ Compute all strings that are one edit away from `word` using only
            the letters in the corpus
        
            Args:
                word (str): The word for which to calculate the edit distance
            Returns:
                set: The set of strings that are edit distance one from the \
                provided word 
        """
        
        word = word.lower()
        if self._check_if_should_check(word) is False:
            return {word}

        #letters    = 'abcdefghijklmnopqrstuvwxyz'
        letters = self._word_frequency.letters
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)
    
    def edit_distance_2(self, word):
        """ Compute all strings that are two edits away from `word` using only
            the letters in the corpus
        
            Args:
                word (str): The word for which to calculate the edit distance
            Returns:
                set: The set of strings that are edit distance two from the \
                provided word 
        """
        word = word.lower()
        return [ e2 for e1 in self.edit_distance_1(word) for e2 in self.edit_distance_1(e1) ]
    
    # This is similar to edit_distance_2, just faster so it doesn't compute edit_distance_1 twice
    def __edit_distance_alt(self, words):
        """ Compute all strings that are 1 edits away from all the words using
            only the letters in the corpus
        
            Args:
                words (list): The words for which to calculate the edit distance
            Returns:
                set: The set of strings that are edit distance two from the \
                provided words 
        """
        words = [x.lower() for x in words]
        return [e2 for e1 in words for e2 in self.edit_distance_1(e1)]
    
    # Check if string is a punctuation or a number
    @staticmethod
    def _check_if_should_check(word):
        if len(word) == 1 and word in string.punctuation:
            return False
        
        try: #check if is a number (int, float, ...)
            float(word)
            return False
        except ValueError:
            pass
        return True
        
