""" Additional utility functions """

import sys
import re
import contextlib
import json

print(sys.version_info)
"""
if sys.version_info < (3, 0):
    import io #python 2 text file encoding support
    
    OPEN = io.open
    
else:
    OPEN = open
""" 
    
@contextlib.contextmanager
def load_file(filename):
    """ Context manager to handle opening a gzip or text file correctly and
        reading all the data
        
        Args:
            filename (str): The filename to open
            encoding (str): The file encoding to use
        Yields:
            str: The string data from the file read
    """
    try:
        #with gzip.open(filename, mode="rt") as f:
            #yield f.read()
         #with open(filename) as data:
            #yield json.load(data)
        
        with open(filename) as f:
            yield f.read()
            
    #except (OSError, IOError) as e:
        #print(e)
    except Exception as e:
        print(e)
    

            
def _parse_into_words(text):
    """ Parse the text into words; currently removes punctuation
        
        Args:
            text (str): The text to split into words
    """
    # TODO: 
    # Check if using spaCy here is better
    return re.findall(r"\w+", text.lower())

def load_entities(filename):
    """ Handle opening entity files correctly and
        reading all the data
        
        Args:
            filename (str): The filename to open
            #encoding (str): The file encoding to use
        Yields:
            str: The string data from the file read
    """
    
    #Check ner ExtractMovieEntities() later
    return False