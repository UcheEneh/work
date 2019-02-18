from __future__ import division, unicode_literals

""" Unit test """

import unittest
import os

from spellchecker import SpellChecker

class TestSpellChecker(unittest.TestCase):
    
    
    def test_correction(self):
        spell = SpellChecker(language='en')
        
        self.assertEqual(spell.correction('ths'), 'the')
        self.assertEqual(spell.correction('ergo'), 'ergo')
        self.assertEqual(spell.correction('alot'), 'a lot')
        self.assertEqual(spell.correction('this'), 'this')
        self.assertEqual(spell.correction('-'), '-')
        self.assertEqual(spell.correction('1213'), '1213')
        self.assertEqual(spell.correction('1213.9'), '1213.9')
    
    def test_candidates(self):
        ''' test spell checker candidates '''
        spell = SpellChecker(language='en')
        cands = {'tes', 'tps', 'th', 'thi', 'tvs', 'tds', 'tbs', 'bhs', 'thf',
                 'chs', 'tis', 'thes', 'tls', 'tho', 'thu', 'thr', 'dhs',
                 "th'", 'thus', 'ts', 'ehs', 'tas', 'ahs', 'thos', 'thy',
                 'tcs', 'nhs', 'the', 'tss', 'hs', 'lhs', 'vhs', "t's", 'tha',
                 'whs', 'ghs', 'rhs', 'this'}
        self.assertEqual(spell.candidates('ths'), cands)
        self.assertEqual(spell.candidates('the'), {'the'})
        self.assertEqual(spell.candidates('-'), {'-'})
        
    def test_words(self):
        ''' rest the parsing of words '''
        spell = SpellChecker(language='en')
        res = ['this', 'is', 'a', 'test', 'of', 'this']
        self.assertEqual(spell.split_words('This is a test of this'), res)
    
    """
    def test_load_external_dictionary(self):
        ''' test loading a local dictionary '''
        here = os.path.dirname(__file__)
        filepath = '{}/resources/small_dictionary.json'.format(here)
        spell = SpellChecker(language=None, local_dictionary=filepath)
        self.assertEqual(spell['a'], 1)
        self.assertTrue('apple' in spell)
    
        
    def test_load_text_file(self):
        ''' test loading a text file '''
        here = os.path.dirname(__file__)
        filepath = '{}/resources/small_doc.txt'.format(here)
        spell = SpellChecker()  # just from this doc!
        spell.word_frequency.load_text_file(filepath)
        self.assertEqual(spell['a'], 3)
        self.assertEqual(spell['storm'], 2)
        self.assertFalse('awesome' in spell)
        self.assertTrue(spell['whale'])
        self.assertTrue('waves' in spell)
    """
        
if __name__ == "__main__":
    unittest.main()