import json
import pickle
import os

import shutil
import requests

import re

class GroupLogs:
    """
    Read in the log files and group into the followuíng folders:
    
    - red: bad dialogue
    - yellow: to be checked
    - green: good dialogues
    
    Arguments:
        - path_logs: the path to the logs
        - mturk_session: the mturk dev session 
            
    Returns:
        - A word file which shows the necessary information from the logs
    """
    
    def __init__(self, path_logs, mturk_session):
        self.path_results = os.path.join(path_logs + "/output/grouped_logs/", mturk_session)
        self.path_logs = os.path.join(path_logs, mturk_session)
        self.regex_list = ['/done', '/noreply']
        
        self.red_path = os.path.join(self.path_results, "red/")
        self.yellow_path = os.path.join(self.path_results, "yellow/")
        self.green_path = os.path.join(self.path_results, "green/") 
        
    def run(self, global_rdr):
        # This if condition is for using the imported reader class
        # Differentiates between when called from here or from the run.py file (change style later)
        if not global_rdr:
            logs_reader = rdr.ReadLogs(self.path_logs)       
        else:
            logs_reader = global_rdr.ReadLogs(self.path_logs)
        
        # This returns a list of the speakers userid in each meetup room and the corresponding list of json logtexts 
        self.list_users, self.list_logtext = logs_reader.run()
        
        if self._seperate_logs():
            print("DONE")
        else:
            print("Error writing to document")
            
    def _seperate_logs(self):
        """
        Check through the dialogue to find the criterias that would make it
            a good, okay or bad conversation
        """
        red_logs, yellow_logs, green_logs = [], [], []
        story_list, room_list = []
        group_list = []
        
        for _users, single_logtext in zip(self.list_users, self.list_logtext):
            good = True
            for item in single_logtext:
                dialogue_list = []
                if item['user']['name'] == "Moderator" and item['type'] == "story_type":
                    story_list.append(item['story_type'])
                    room_list.append(item['room']['name'])
                
                # Get dialogue to a list
                if item['type'] == 'text' and item['user']['id'] in _users:                  
                    dialogue_list.append(item['msg'])
                
                # Check if dialogue less than 4 utterances
                if len(dialogue_list) < 4:
                    self.red_logs.append(str(single_logtext))
                    good = False
                    
                # Check if /done, /noreply in dialogue
                elif len(dialogue_list) > 4:
                    #Work on this to get the last three utterances
                    for _sentence in dialogue_list[:3]: 
                        for regex in self.regex_list:
                            matches = re.finditer(regex, _sentence, re.MULTILINE)
                            
                            for match in matches:
                                if match.group():
                                    self.yellow_logs.append(str(single_logtext))
                                    good = False
                                    break
                # if not, then append to green
                if good:  
                    self.green_logs.append(str(single_logtext))
        
        # Move logs to new folders       
        self._move(red_logs, self.path_logs, self.red_path)
            
        
        
        # Save a dict file with info
        group_list.append({'red': red_logs,
                           'yellow': yellow_logs,
                           'green': green_logs
                           })
                   
    def _saver(self, _document, _fname):
        if not os.path.exists(self.path_results):
            os.makedirs(self.path_results)
        
        doc_path = os.path.join(self.path_results, _fname)
        _document.save(doc_path)
        
    def _move(self, file, source, dest):
        if not os.path.exists(dest):
            os.makedirs(dest)
        
        # Either f is a single file or a list of logfiles
        # Using list
        for f in file:
            shutil.move(source, dest)
              
        
if __name__ == '__main__':
    import reader as rdr   
    #mturk_session = "moviedatagen_real_test_2/"
    mturk_session = "data_collection_part_1/"

    gl = GroupLogs(path_logs="../logfiles/", mturk_session=mturk_session)
    gl.run("")