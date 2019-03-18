import glob
import json
import pickle
import os
import requests
from libs import sentence_patterns
import copy

from libs import moviedatalib
from sources import named_entity_resolution

# ----- class implementation -----
# Process Logfiles
# --------------------------------
class ProcessLogs:
    """
    This class reads in the log files and extracts the necessary information needed 
    for the neural network model training
    """
    
    def __init__(self, path_logs, mturk_session, path_stories, path_data):
        # Fabian
        #self.path_results = os.path.join(path_logs + "/../output/", mturk_session)
        #self.path_logs = path_logs

        # Uche
        self.path_results = os.path.join(path_logs + "/output/", mturk_session)
        self.path_logs = os.path.join(path_logs, mturk_session)

        self.stories = pickle.load(file=open(path_stories, 'rb'))
        self.movie_data = pickle.load(file=open(path_data, 'rb'))

        self.sp = sentence_patterns.AttitudesV2()
        self.ner = named_entity_resolution.NamedEntityResolution(path_data=self.movie_data,)

        self.log = None
        self.original_dialogue = None
        self.original_dialogue_cutted = None
        self.original_dialogue_ner = None
        self.original_dialogue_ner_spelling = None
        #self.URL_NLP = "https://0954e67f-a89f-400c-9205-corenlp.azurewebsites.net/?properties={\"annotators\": \"tokenize,ssplit\", \"date\": \"2018-09-13T14:46:47\"}&pipelineLanguage=en"
        
    # ----- public functions ---------------------------------------------------------------
    def run(self, global_rdr):
        if not global_rdr:
            logs_reader = rdr.ReadLogs(self.path_logs)       
        else:
            logs_reader = global_rdr.ReadLogs(self.path_logs)           
        
        #logs_reader returnsa list of the users in each logfile and the corresponding list of json logtexts 
        self.list_users, self.list_logtext = logs_reader.run()

        cnt = len(self.list_logtext)
        idx = 1
        for _users, single_logtext in zip(self.list_users, self.list_logtext):
            print("Processing log num. " + str(idx) + " of " + str(cnt) + " total logs.")
            idx += 1
            result = self._processed_dialogue(_users, single_logtext)
            if result:
                result_quality = self._check_result(result)
                if result_quality == "healthy":
                    self._save(result, self.fname, subfolder="healthy")
                    # put visual log here
                elif result_quality == "problems":
                    self._save(result, self.fname, subfolder="problems")
                    # put visual logfile here
                elif result_quality == "corrupted":
                    self._save(result, self.fname, subfolder="corrupted")  # TODO: Here only visual logfile
            else:
                self._save("no result!", self.fname, subfolder="no_result")


        print("\nProcessed result has been saved into {}".format(self.path_results))
        print("DONE")
        
    def _processed_dialogue(self, _users, _log_text):
        """
        This function extracts and writes the necessary information needed for training
        
        Returns:
        - pickle file containing the following info:
            'user_id': id of conversation
            'knowledge': knowledge_dict,
            'attitudes': attitudes_dict,
            'named_entities':
            'dialogue_orig': original dialogue
            'dialogue_processesd': tokenized dialogue
            'dialogue_named_entity': dialogue after name entity resolution
        """
        # Rearrange speaker turns and tokenize the dialogue
        self.original_dialogue = self._order_speaker_turns(_users, _log_text)  # TODO: Remove tokenizer here and do it in NER
        
        # Then create new output file
        single_sample_output = {}
        # dialogue = _dialogue_name
        attitudes_dict, knowledge_dict, question_dict, answer_dict = {}, {}, {}, {}
        knowledge_dict_v2 = {'first_speaker': [], 'second_speaker': []}
        fact0, fact1, answer0, answer1 = {}, {}, {}, {}
        story_id = ""

        # --- analyse log file ----------------------------------------------------------------------------------------
        # Author: Uche
        # This loop goes through all entries of a slurk-logfile and extracts all relevant information.
        # -------------------------------------------------------------------------------------------------------------
        for item in _log_text:
            # Get type of story and name of logfile
            if item['user']['name'] == "Moderator" and item['type'] == "story_type":
                #story = item['story_type']     # redundant
                meetup_name = item['room']['name']
                user_id = item['timestamp-iso'] + "-" + item['room']['name']
                # use for naming the file
                # this replace is performed because files cant be saved with character ":"
                self.fname = user_id.replace(":", "-")
                continue

            # Check for story ID and collect.
            if "story_id" in item:
                story_id = item['story_id']

            # Check for table-entities and collect. (Same for both user!)
            if item['type'] == "table_entities":
                table_entity = item['table']
                continue

            if item['type'] == 'table_traits':               
                if item['user']['id'] == _users[0]:
                    attitudes_list = item['table']
                    attitudes_dict.update({'first_speaker': attitudes_list})
                if item['user']['id'] == _users[1]:
                    attitudes_list = item['table']
                    attitudes_dict.update({'second_speaker': attitudes_list})
                continue

            if item['type'] == 'table_facts':               
                if item['user']['id'] == _users[0]:
                    # Input facts correspondingly (key = topic, value = fact)
                    # Note: zip only works if the two iterations are of same length
                    for count, (topic, fact) in enumerate(zip(item['table'][0], item['table'][1])): 
                        #fact0_dict.update({topic: fact})
                        fact0[count] = {topic: fact}
                        knowledge_dict_v2['first_speaker'].append({'entity': topic,
                                                                   'fact': fact})
                    knowledge_dict.update({'first_speaker': fact0})
                
                if item['user']['id'] == _users[1]:
                    for count, (topic, fact) in enumerate(zip(item['table'][0], item['table'][1])): 
                        #fact1_dict.update({topic: fact}) 
                        fact1[count] = {topic: fact}
                        knowledge_dict_v2['second_speaker'].append({'entity': topic,
                                                                   'fact': fact})
                    knowledge_dict.update({'second_speaker': fact1})
                continue

            if item['type'] == 'table_questions':
                # Speaker 1
                if item['user']['id'] == _users[0]:
                    question_list = item['table']
                    question_dict.update({'first_speaker': question_list})
                # Speaker 2
                if item['user']['id'] == _users[1]:
                    question_list = item['table']
                    question_dict.update({'second_speaker': question_list})
                continue

            if item['type'] == 'table_answers':
                # Speaker 1
                if item['user']['id'] == _users[0]:
                    for count, (entity, answer) in enumerate(zip(item['table'][0], item['table'][1])):
                        answer0[count] = {entity: answer}
                        knowledge_dict_v2['first_speaker'].append({'entity': entity,
                                                                   'fact': answer})
                    answer_dict.update({'first_speaker': answer0})
                # Speaker 2
                if item['user']['id'] == _users[1]:
                    for count, (entity, answer) in enumerate(zip(item['table'][0], item['table'][1])):
                        answer1[count] = {entity: answer}
                        knowledge_dict_v2['second_speaker'].append({'entity': entity,
                                                                   'fact': answer})
                    answer_dict.update({'second_speaker': answer1})
                continue
        # --- check if dialogue is valid ------------------------------------------------------------------------------
        if story_id == "":
            return False
        # --- cut dialogue --------------------------------------------------------------------------------------------
        # self.original_dialogue_cutted = self._check_out_of_topic(self.original_dialogue)
        self.original_dialogue_cutted = copy.deepcopy(self.original_dialogue)

        # --- restore story-facts from stories.pkl and data.pkl -------------------------------------------------------
        # This is more or less a hack. The stories, we generated, do not contain the kg-triple information.
        # Therefore the following lines restore them.
        # -------------------------------------------------------------------------------------------------------------
        story, movie_title = self._get_story(story_id=story_id)
        fact_value_dict = self._get_facts(movie_title=movie_title, story=story)

        # --- generate fact-information -------------------------------------------------------------------------------
        # Restoring the fact triples in the form of: subject, relation, object
        # -------------------------------------------------------------------------------------------------------------
        facts_original = {'first_speaker': self._generate_fact_triples(knowledge_dict=knowledge_dict_v2['first_speaker'],
                                                              fact_value_dict=fact_value_dict,
                                                              movie_title=movie_title),
                 'second_speaker': self._generate_fact_triples(knowledge_dict=knowledge_dict_v2['second_speaker'],
                                                               fact_value_dict=fact_value_dict,
                                                               movie_title=movie_title)}

        # --- generate attitude-information ---------------------------------------------------------------------------
        # Restoring the attitude triples in the form of: subject, relation, object
        # -------------------------------------------------------------------------------------------------------------
        attitudes_original = self.generate_attitude_triples(fact_value_dict=fact_value_dict,
                                                   attitude_dict=attitudes_dict,
                                                   attitude_candidates=story[2]['attitudes'],
                                                   movie_title=movie_title)

        # --- named entity resolution ---------------------------------------------------------------------------------
        # Generates the delexicalized dialogue, facts and attitudes with the local dictionary.
        # -------------------------------------------------------------------------------------------------------------
        self.original_dialogue_ner, named_entity_dict, \
        facts, attitudes = self.ner.run_through_dialogue(dialogue=self.original_dialogue_cutted,
                                                         logfile_info=[movie_title, meetup_name],
                                                         facts_original=facts_original,
                                                         attitudes_original=attitudes_original)

        # --- spelling correction -------------------------------------------------------------------------------------
        self.original_dialogue_ner_spelling = copy.deepcopy(self.original_dialogue_ner)

        # --- generate one sample for training ------------------------------------------------------------------------
        single_sample_output.update({
            'log_file_name': user_id,
            'story_type': story,
            'story_id': story_id,
            'story_entities': table_entity,
            'facts_original': facts_original,
            'attitudes_original': attitudes_original,
            'facts': facts,
            'attitudes': attitudes,
            'questions': question_dict,
            'answers': answer_dict,
            'named_entity_dict': named_entity_dict,
            'dialogue_original': self.original_dialogue,
            'dialogue_cutted': self.original_dialogue_cutted,
            'dialogue_ner': self.original_dialogue_ner,
            'dialogue_ner_spelling': self.original_dialogue_ner_spelling
            })


        return single_sample_output

    # -----------------------------------------------------------------------------------------------------------------
    # --- protected functions -----------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------
    def _order_speaker_turns(self, _users, _log_text):
        """
        This function rearranges the speaker turns for speakers with multiple turns at once 
        
        Return:
            - dialogue_list: this contains the reordered dialogue giving one turn for one paragraph
            - dialogue_tok_list: contains the tokenized version of sentences in dialogue_list 
        """
        
        #First clean the dialogue speaker term and create the list here
        curr_userid = 0
        dialogue_list = []
        #dialogue_tok_list = []
        tmp_msg = ""
        #tmp_msg_tk = ""
        
        for item in _log_text:           
            #Rearrange the dialogue orders so that its just one line per speaker turn
            if item['type'] == 'text' and item['user']['id'] in _users:                
                if item['user']['id'] == curr_userid:
                    #Update the dialogue_list if the same speaker has used two turns
                    msg = tmp_msg + " [EOU] " + item['msg']
                    dialogue_list[len(dialogue_list) - 1] = msg
                    
                    #Perform tokenization
                    # Add a ". " after each sentence for single speaker with multiple turns
                    # msg_tk = tmp_msg_tk + ". " + item['msg']
                    # tokens = self._tokenize(msg_tk)
                    # dialogue_tok_list[len(dialogue_tok_list) - 1] = tokens
                    
                    tmp_msg = msg
                    # tmp_msg_tk = msg_tk
                else:
                    #First check if dialogue already contains a fullstop before adding new one
                    #msg_punct = item['msg'] + "."
                    #dialogue_list.append(msg_punct)
                    
                    dialogue_list.append(item['msg'])
                    # tmp_msg is used incase a speaker uses two turns so we can put each of them together
                    tmp_msg = item['msg']   
                    # tmp_msg_tk = item['msg']
                    
                    #Perform tokenization
                    # tokens = self._tokenize(item['msg'])
                    # dialogue_tok_list.append(tokens)
                
                curr_userid = item['user']['id']                

        # remove "nice to chat with you" utterances at the end.
        # dialogue_tok_list = ProcessLogs._check_out_of_topic(dialogue_tok_list)

        return dialogue_list #, dialogue_tok_list

    '''    
    def _tokenize(self, _text): 
        """
        Tokenizer function for the dialogue
        
        Argument:
            - _text: this contains a single sentence
            
        Returns:
            - tok_list: this contains the tokenized form of the input sentence
        """
        tok_list = []
        r = requests.post(self.URL_NLP,
                           data=_text.encode('utf-8'))
        my_json = r.content.decode('utf-8')
        x = json.loads(my_json)
                
        for _sentence in x['sentences']:
            for _word in _sentence['tokens']:
                tok_list.append(_word['word'])                    
        return tok_list        
    '''

    def _save(self, result, filename, subfolder=""):
        if not os.path.exists(os.path.join(self.path_results, subfolder)):
            os.makedirs(os.path.join(self.path_results, subfolder))
        with open(os.path.join(self.path_results, subfolder, filename + '.pkl'), 'wb') as outfile:
            #json.dump(result, outfile)
            pickle.dump(result, outfile)

    def _check_result(self, result):
        # check for speaker turns
        problems = 0

        if len(result['dialogue_original']) < 3:
            return "corrupted"
        elif len(result['dialogue_original']) < 5:
            problems += 0

        cnt = 0
        for utterance in result['dialogue_original']:
            if len(utterance.split(" ")) < 4:
                cnt += 1
        if cnt > int(0.4*len(result['dialogue_original'])):
            return "problems_short_answers"

        dialogues = []
        cnt = 0
        for utterance in result['dialogue_original']:
            if utterance not in dialogues:
                dialogues.append(utterance)
            else:
                cnt += 1
        if cnt > 0:
            return "problems_multiple_utterances_same"

        if problems > 3:
            return "corrupted"
        elif problems > 0:
            return "problems"
        else:
            return "healthy"

    def _get_story(self, story_id):
        """ Given a story_id this function returns the correct story and the name of the movie. """
        for story in self.stories:
            if story[2]['story_id'] == story_id:
                if story[2]['story_type'] == "PersonToMovieStory":
                    movie_title = story[0]['entities'][2]
                else:
                    movie_title = story[0]['entities'][0]
                return story, movie_title

    @staticmethod
    def _check_out_of_topic(dialogue_tok_list):
        # check for out-of-topic utterances
        idx_to_check = int(0.8 * (len(dialogue_tok_list)))

        for idx, utterance in enumerate(dialogue_tok_list):
            out_of_topic = False
            if idx >= idx_to_check:
                if "done" in utterance or "chat" in utterance or "chatting" in utterance:
                    dialogue_tok_list = dialogue_tok_list[:idx]
                    break
        return dialogue_tok_list

    def _get_facts(self, movie_title, story):
        facts = {}
        for movie in self.movie_data['movies']:
            if movie.title == movie_title:
                entities = story[2]['entities']
                persons = []
                facts['used_trivia'] = movie._trivia_ref._trivia['used']
                for entity in story[0]['entities'] + story[1]['entities']:
                    if entity not in persons and entity != movie_title:
                        persons.append(entity)
                        if entity in movie._person_ref:
                            facts['used_trivia'] += movie._person_ref[entity]._trivia_ref._trivia['used']
                facts['persons'] = persons

                for entity in entities:
                    if entity == "movie":
                        facts['movie'] = ""
                    elif entity == "countries":
                        facts[entity] = str(movie.get_fact(entity)[0])
                    elif entity == "genres":
                        facts[entity] = movie.get_fact(entity)  # TODO: Genre 0 and 1?!
                    elif entity == "actor-0" or entity == "actor-1" or entity == "movie_act":
                        facts[entity] = movie.get_fact("actors")
                    else:
                        facts[entity] = str(movie.get_fact(entity))
                return facts

    def _generate_fact_triples(self, knowledge_dict, fact_value_dict, movie_title):
        facts = []
        for knowledge in knowledge_dict:
            fact_triple = {
                'subject': "",
                'relation': "",
                'object': ""
            }
            if knowledge['entity'] == movie_title:
                fact_triple['subject'] = movie_title
                # check for trivia
                if knowledge['fact'] in fact_value_dict['used_trivia']:
                    fact_triple['relation'] = "has_trivia"
                    fact_triple['object'] = knowledge['fact']
                    facts.append(fact_triple)
                    continue
                else:
                    # check for plot
                    if "plot" in fact_value_dict:
                        if knowledge['fact'] == fact_value_dict['plot']:
                            fact_triple['relation'] = "has_plot"
                            fact_triple['object'] = fact_value_dict['plot']
                            facts.append(fact_triple)
                            continue
                    # check for writer
                    if "writer" in fact_value_dict:
                        if (fact_value_dict['writer'] in knowledge['fact']) and ("writer" in knowledge['fact'].lower()):
                            fact_triple['relation'] = "has_writer"
                            fact_triple['object'] = fact_value_dict['writer']
                            facts.append(fact_triple)
                            continue
                    # check for director
                    if "director" in fact_value_dict:
                        if fact_value_dict['director'] in knowledge['fact']:
                            fact_triple['relation'] = "has_director"
                            fact_triple['object'] = fact_value_dict['director']
                            facts.append(fact_triple)
                            continue
                    # check for actor
                    if "actor-0" in fact_value_dict or "actor-1" in fact_value_dict or "movie_act" in fact_value_dict:
                        for person in fact_value_dict['persons']:
                            if person in knowledge['fact']:
                                fact_triple['relation'] = "has_actor"
                                fact_triple['object'] = person
                                facts.append(fact_triple)
                                for imdb_person in fact_value_dict['actor-0']:
                                    if str(imdb_person) == person:
                                        role = imdb_person.notes
                                        if role in knowledge['fact']:
                                            fact_triple = {
                                                'subject': movie_title,
                                                'relation': "has_role",
                                                'object': role
                                            }
                                            facts.append(fact_triple)
                                            fact_triple = {
                                                'subject': person,
                                                'relation': "has_role",
                                                'object': role
                                            }
                                            facts.append(fact_triple)
                                continue
                    # check for year
                    if "year" in fact_value_dict:
                        if fact_value_dict['year'] in knowledge['fact']:
                            fact_triple['relation'] = "has_release_year"
                            fact_triple['object'] = fact_value_dict['year']
                            facts.append(fact_triple)
                            continue
                    # check for countries
                    if "countries" in fact_value_dict:
                        if fact_value_dict['countries'] in knowledge['fact']:
                            fact_triple['relation'] = "has_shot_location"
                            fact_triple['object'] = fact_value_dict['countries']
                            facts.append(fact_triple)
                            continue
                    # check for budget
                    if "budget" in fact_value_dict:
                        if fact_value_dict['budget'] in knowledge['fact']:
                            fact_triple['relation'] = "has_budget"
                            fact_triple['object'] = fact_value_dict['budget']
                            facts.append(fact_triple)
                            continue
                    # check for certificate
                    if "certificate" in fact_value_dict:
                        if fact_value_dict['certificate'] in knowledge['fact']:
                            fact_triple['relation'] = "has_age_certificate"
                            fact_triple['object'] = fact_value_dict['certificate']
                            facts.append(fact_triple)
                            continue
                    # check for genres
                    if "genres" in fact_value_dict:
                        if fact_value_dict['genres'][0] in knowledge['fact']:
                            fact_triple['relation'] = "has_genre"
                            fact_triple['object'] = fact_value_dict['genres'][0]
                            facts.append(fact_triple)
                            if len(fact_value_dict['genres']) > 1:
                                fact_triple = {
                                    'subject': movie_title,
                                    'relation': "has_genre",
                                    'object': fact_value_dict['genres'][1]
                                }
                            facts.append(fact_triple)
                            continue
            else:
                # TODO: Check if this is True for EVERY story.
                # (Could be the problem, that an actor-entity is only a writer-actor-director fact)
                fact_triple['subject'] = knowledge['entity']
                fact_triple['relation'] = "has_trivia"
                fact_triple['object'] = knowledge['fact']
                facts.append(fact_triple)

        return facts

    def generate_attitude_triples(self, fact_value_dict, attitude_dict, attitude_candidates, movie_title):
        stop = "here"
        attitudes = {
            'first_speaker': [],
            'second_speaker': []
        }
        # 2 loop iterations (first and second speaker)
        for key, value in attitude_dict.items():
            # for all attitudes that are in the story for a specific speaker
            for attitude_from_dict in value:
                attitude = {}
                if movie_title in attitude_from_dict:
                    replaced_attitude = attitude_from_dict.replace(movie_title, "MOVIE")
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="positive", return_all=True,
                                                          strength=1):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 5
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="positive", return_all=True,
                                                          strength=2):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 4
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="positive", return_all=True,
                                                          strength=3):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 3
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="negative", return_all=True,
                                                          strength=1):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 2
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="negative", return_all=True,
                                                          strength=2):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 1
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.movie(movie="MOVIE", attitude="unknown", return_all=True):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 0
                        attitudes[key].append(attitude)
                        continue
                person = ""
                for person in fact_value_dict['persons']:
                    if person in attitude_from_dict:
                        person = person
                        break
                if person != "":
                    replaced_attitude = attitude_from_dict.replace(person, "PERSON")
                    replaced_attitude = replaced_attitude.replace("actor", "TYPE")
                    replaced_attitude = replaced_attitude.replace("director", "TYPE")
                    replaced_attitude = replaced_attitude.replace("writer", "TYPE")
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="positive",
                                                           return_all=True, strength=1):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 5
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="positive",
                                                           return_all=True, strength=2):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 4
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="positive",
                                                           return_all=True, strength=3):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 3
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="negative",
                                                           return_all=True, strength=1):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 2
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="negative",
                                                           return_all=True, strength=2):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 1
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.person(person="PERSON", type="TYPE", attitude="unknown",
                                                           return_all=True):
                        attitude['subject'] = person
                        attitude['relation'] = "has_general_bot_attitude"
                        attitude['object'] = 0
                        attitudes[key].append(attitude)
                        continue
                if 'countries' in fact_value_dict:
                    if fact_value_dict['countries'] in attitude_from_dict:
                        replaced_attitude = attitude_from_dict.replace(fact_value_dict['countries'], "COUNTRY")
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="positive",
                                                                  return_all=True, strength=1):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 5
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="positive",
                                                                  return_all=True, strength=2):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 4
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="positive",
                                                                  return_all=True, strength=3):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 3
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="negative",
                                                                  return_all=True, strength=1):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 2
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="negative",
                                                                  return_all=True, strength=2):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 1
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.countries(countries=["COUNTRY"], attitude="unknown",
                                                                  return_all=True):
                            attitude['subject'] = fact_value_dict['countries']
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 0
                            attitudes[key].append(attitude)
                            continue
                if 'genres' in fact_value_dict:
                    if fact_value_dict['genres'][0] in attitude_from_dict:
                        replaced_attitude = attitude_from_dict.replace(fact_value_dict['genres'][0], "GENRE")
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="positive",
                                                              return_all=True, strength=1):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 5
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="positive",
                                                              return_all=True, strength=3):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 4
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="positive",
                                                              return_all=True, strength=4):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 3
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="negative",
                                                              return_all=True, strength=1):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 2
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="negative",
                                                              return_all=True, strength=2):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 1
                            attitudes[key].append(attitude)
                            continue
                        if replaced_attitude in self.sp.genre(genre="GENRE", attitude="unknown",
                                                              return_all=True):
                            attitude['subject'] = fact_value_dict['genres'][0]
                            attitude['relation'] = "has_general_bot_attitude"
                            attitude['object'] = 0
                            attitudes[key].append(attitude)
                            continue
                if 'certificate' in fact_value_dict:
                    replaced_attitude = attitude_from_dict.replace(movie_title, "MOVIE")
                    if replaced_attitude in self.sp.certificate(movie="MOVIE", attitude="positive",
                                                                return_all=True):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_bot_certificate_attitude"
                        attitude['object'] = 3
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.certificate(movie="MOVIE", attitude="negative",
                                                                return_all=True):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_bot_certificate_attitude"
                        attitude['object'] = 2
                        attitudes[key].append(attitude)
                        continue
                    if replaced_attitude in self.sp.certificate(movie="MOVIE", attitude="unknown",
                                                                return_all=True):
                        attitude['subject'] = movie_title
                        attitude['relation'] = "has_bot_certificate_attitude"
                        attitude['object'] = 0
                        attitudes[key].append(attitude)
                        continue
        return attitudes


if __name__ == '__main__':
    import reader as rdr
    #mturk_session = "versuchsreihe3/"
    mturk_session = ""
    
    plogs = ProcessLogs(path_logs="../logfiles/", mturk_session=mturk_session)
    plogs.run("")
