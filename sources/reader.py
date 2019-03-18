import os
import json
import glob
 
class ReadLogs:
    """
        Reads in the log files and returns the relevant information only
        
        Arguments:
            - path_logs: the path to the logs
            - mturk_session: the mturk dev session 
        
        Return:
            - list_users: A list of the user ids of the two speakers in each logfile
            - list_logtext: A list of the full json text from each logfile 
    """
    
    def __init__(self, path_logs):        
        self.path_logs = path_logs
        
    def run(self):
        #Load the logs
        logs = glob.glob(self.path_logs + '/*.log')      #get all files ending in ".log" alone
        log_meetup = []
        
        #dict_output = {}
        list_users = []
        list_logtext = []
        
        if len(logs) == 0:
            print("No Logs found in '" + self.path_logs + "'. Finished.")
            return
        else:
            print("\nThe following logs were found:")
            for log in logs:
                print(str(log))
                if "meetup" in log:
                    log_meetup.append(log)
        
        for single_log in log_meetup:                                                           
            with open(single_log) as log_file:
                log_text = json.load(log_file)                
                users = []
                #Get id of users in the chat room
                for item in log_text:
                    # Prevent double entrance of multiple instances of same user
                    # And don't include the moderator id  
                    if item['user']['id'] in users or item['user']['name'] == "Moderator":  
                        continue
                    else:
                        users.append(item['user']['id'])            
            
            list_users.append(users)
            list_logtext.append(log_text)
            #dict_output[count] = {users : log_text}
            
        #print("DONE")
        return list_users, list_logtext


if __name__ == '__main__':
   rdr = ReadLogs(path_logs="../logfiles/")
   rdr.run()   
