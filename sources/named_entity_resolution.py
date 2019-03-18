# import json
import pickle
# import glob
import os
import copy

# import nltk
import spacy
import re

# from imdb import IMDb
# from tqdm import tqdm
# from sources import reader as rdr

class ExtractMovieEntity:
    def __init__(self, path_data, already_loaded=False):
        self.path_full_data = path_data
        # For run_through_dialogue
        if already_loaded:
            self.full_data = path_data
            print('Full movie database loaded!')
        else:
            # Load the database of collected movie information
            if not os.path.isfile(self.path_full_data):
                print("Database (data.pkl) of collected movie information not available in path given: ", path_data)
            else:
                with open(self.path_full_data, 'rb') as f:
                    self.full_data = pickle.load(f)
                    print('Full movie database loaded!')

    def create_dict_of_entities(self, _users=None, _log_text=None, logfile_info=None):
        """
        Create two dicts:
            One for person entities, the other for other entities
        """

        ###################################################
        #        GET THE NAME OF MAIN MOVIE IN LOG        #
        ###################################################

        if logfile_info is None:
            # I assume the first table fact entity from the first speaker is always the movie name
            # except for story of type: PersonToTrivia, where the movie name is the second entity
            # Maybe better way to get movie name
            person_story = False
            for item in _log_text:
                if item['type'] == 'story_type' and item['story_type'] == 'PersonToMovieStory':
                    person_story = True
                    break

            for item in _log_text:
                if item['type'] == 'table_facts' and item['user']['id'] == _users[0]:
                    if person_story is True:
                        movie_name = item['table'][0][2]
                    else:
                        movie_name = item['table'][0][0]
                    meetup_name = item['room']['name']
                    print("\nLog: ", meetup_name)
                    print("Movie name: ", movie_name)
                    print("-----------------------")
                    break
        # Read from processed log dialogue
        else:
            movie_name = logfile_info[0]
            meetup_name = logfile_info[1]
            print("\nLog: ", meetup_name)
            print("Movie name: ", movie_name)
            print("-----------------------")

        #########################################################
        #        CHECK IF MOVIE DATA IN CREATED DATABASE        #
        #########################################################
        self.title = None
        for movie in self.full_data['movies']:
            if movie_name == movie.title:
                self.title = movie.title
                break

        ########################################################################################
        #    CREATE A DICT WHICH CONTAINS ALL ENTITIES IN FACTS TABLE AND THEIR SUBSTITUTES    #
        ########################################################################################
        """
        # Entities we need to look for:
            actors, budget, certificate, countries, 
            director, genres, writer, year 
        """
        list_actor, list_countries, list_genres, list_movies = ([], [], [], [])
        person_entities = {}  # actor, director, writer
        info_entities = {}  # movie title, budget, year, certificate,...

        #######################################
        #        Input main movie name        #
        #######################################
        if self.title not in list_movies:
            list_movies.append(self.title)
            info_entities.update({self.title: 'movie#' + str(len(list_movies) - 1)})
        # TO DO:
        # Check for other movies that may have been mentioned which isn't main movie

        ######################################
        #        Input other entities        #
        ######################################
        #for entity in tqdm(movie._facts):
        for entity in movie._facts:
            if entity == 'actors':
                actors = movie.get_fact('actors')
                for actor in actors:
                    # for actor in movie._facts['actors']:
                    if str(actor) not in list_actor:
                        list_actor.append(str(actor))
                        person_entities.update({str(actor): 'actor#' + str(len(list_actor) - 1)})
                continue

            if entity == 'budget':
                # only one budget considered
                info_entities.update({movie.get_fact(entity): 'budget#0'})
                continue

            if entity == 'certificate':
                info_entities.update({movie.get_fact(entity): 'certificate#0'})
                continue

            if entity == 'countries':
                for country in movie._facts[entity]:
                    list_countries.append(country)
                    info_entities.update({country: 'country#' + str(len(list_countries) - 1)})
                continue

            if entity == 'genres':
                for genre in movie._facts[entity]:
                    list_genres.append(genre)
                    info_entities.update({genre: 'genre#' + str(len(list_genres) - 1)})
                continue

            if entity == 'year':
                # Release year
                # movie_entities.update({movie._facts[entity] : 'year#0'})
                info_entities.update({movie.get_fact(entity): 'year#0'})
                continue

        ###########################################
        #        Input director and writer        #
        ###########################################
        if movie.has_fact('writer=director'):  # or movie.has_fact('director'):
            if movie.get_fact('writer=director') is True:
                entity = str(movie.get_fact('director'))
                # only one director considered
                person_entities.update({entity: 'director#0'})
            else:
                entity = str(movie.get_fact('director'))
                person_entities.update({entity: 'director#0'})

                entity = str(movie.get_fact('writer'))
                person_entities.update({entity: 'writer#0'})
        else:
            entity = str(movie.get_fact('director'))
            person_entities.update({entity: 'director#0'})

            entity = str(movie.get_fact('writer'))
            person_entities.update({entity: 'writer#0'})

        return [person_entities, info_entities], movie_name


class NamedEntityResolution:
    def __init__(self, path_data, path_logs=None, mturk_session=None):
        #self.path_results = os.path.join(path_logs + "/output/", mturk_session)
        self.path_logs = path_logs
        self.mturk_session = mturk_session
        self.path_data = path_data
        # self.DataMovie = DataMovie
        # self.DataPerson = DataPerson
        self.nlp = spacy.load('en_core_web_sm')

    def run_through_dialogue(self, dialogue, logfile_info, facts_original, attitudes_original):
        """
        :param dialogue: pointer
        :param facts_original:   pointer
        :param attitudes_original: pointer
        :return:
        """

        # TODO:
        # Update entities dict to only contain the used entities
        # Use updated version of entities_dict for the entity resolution

        movie_data = self.path_data
        original_dialogue_ = copy.deepcopy(dialogue)
        #_users = users
        #_single_logtext = single_logtext

        mov_ent = ExtractMovieEntity(movie_data, already_loaded=True)
        entities_dict, mov_name = mov_ent.create_dict_of_entities(logfile_info=logfile_info)

        # Check for different variations in movie name during entity resolution
        # For now only perform search if ':' is in movie name. Consider others later e.g ',!'
        self.names_list = []
        if ':' in mov_name:
            self.names_list = self._create_different_searches(mov_name, type="movie")
        else:
            self.names_list.append(mov_name)

        self.list_US, self.list_UK = None, None
        # Check country and make list for entity resolution search if matching
        if "United States" in entities_dict[1]:
            self.list_US = self._create_different_searches(name="United States", type="country")
        if "United Kingdom" in entities_dict[1]:
            self.list_UK = self._create_different_searches(name="United Kingdom", type="country")

        print("\nEntities in the dict: ")
        print("Person: ")
        print(entities_dict[0])
        print("Info: ")
        print(entities_dict[1])
        print("-----------------------")
        # Perform ner
        self.found_person_not_in_entities_dict = {}
        self.original_dialogue_ner = []
        for utterance in original_dialogue_:
            msg_ner = self._implement_resolution(entities_dict, utterance)
            #print(msg_ner)
            self.original_dialogue_ner.append(msg_ner)

        for ner_single_dial in self.original_dialogue_ner:
            print(ner_single_dial)

        if self.found_person_not_in_entities_dict:
            print('\nPeople not matching from the list of given entities: ')
            print(self.found_person_not_in_entities_dict)
        print("....................................................................................................... \
              ..................................................\n")

        #***************************************
        # Perform facts and attitudes named entity resolution
        #***************************************
        # TODO:
        # Update entities dict to only contain the used entities
        # Use updated version of entities_dict for the entity resolution

        # FACTS
        facts_relations = {'has_writer' : "writer",
                           'has_director' : "director",
                           'has_actor' : "actor",
                           'has_release_year' : "year",
                           'has_shot_location' : "country",
                           'has_budget' : "budget",
                           'has_age_certificate' : "certificate",
                           'has_genre' : "genre" }
        facts_ner = copy.deepcopy(facts_original)
        # Loop through each speaker and their facts
        for speaker, full_triple in facts_ner.items():
            # Assuming single speaker has multiple facts given, therefore multiple triples:
            for single_triple in full_triple:
                # Facts table entity
                _subject = single_triple['subject']
                # loop through info_ent_dict and person_ent_dict
                for _dict in entities_dict:
                    if _subject in _dict:
                        single_triple['subject'] = re.sub(_subject, _dict[_subject], single_triple['subject'])
                        continue

                # Facts table value
                _object = single_triple['object']  # copy.copy() shallow copy not working
                if single_triple['relation'] in facts_relations:
                    for _dict in entities_dict:
                        if _object in _dict:
                            single_triple['object'] = re.sub(_object, _dict[_object], single_triple['object'])
                            continue

        # ATTITUDES
        # Not necessary since entity resolution only performed on 'subject'
        # attitudes_relations = {'has_general_bot_attitude': ["movie", "country", "genre", "actor", "director", "writer"],
        #                       'has_bot_certificate_attitude': "certificate" }
        attitudes_ner = copy.deepcopy(attitudes_original)
        # Loop through each speaker
        for speaker, full_triple in attitudes_ner.items():
            # Assuming single speaker has multiple attitudes given, therefore multiple triples:
            for single_triple in full_triple:
                # Attitudes table entity
                _subject = single_triple['subject']
                # loop through info_ent_dict and person_ent_dict
                for _dict in entities_dict:
                    if _subject in _dict:
                        single_triple['subject'] = re.sub(_subject, _dict[_subject], single_triple['subject'])
                        continue

        return self.original_dialogue_ner, entities_dict, facts_ner, attitudes_ner

    def run_through_logs(self, global_rdr):
        """
            Perform the named entity resolution directly on the logfiles
        """
        path_logs = os.path.join(self.path_logs, self.mturk_session)
        path_data = self.path_data

        if not path_data or not path_logs or not self.mturk_session:
            raise Exception("Missing something.")

        if not global_rdr:
            logs_reader = rdr.ReadLogs(self.path_logs)
        else:
            logs_reader = global_rdr.ReadLogs(self.path_logs)
        self.list_users, self.list_logtext = logs_reader.run()

        mov_ent = ExtractMovieEntity(self.path_data)  # , self.DataMovie, self.DataPerson)
        # Perform the operation for each logfile
        for _users, _single_logtext in zip(self.list_users, self.list_logtext):
            # TODO:
            # Update entities dict to only contain the used entities
            # Use updated version of entities_dict for the entity resolution

            entities_dict, mov_name = mov_ent.create_dict_of_entities(_users, _single_logtext)

            # Would be used to check for variations in movie name during entity resolution
            # For now only perform search if ':' is in movie name. Consider others later e.g ',!'
            self.names_list = []
            if ':' in mov_name:
                self.names_list = self._create_different_searches(mov_name, type="movie")
            else:
                self.names_list.append(mov_name)

            self.list_US, self.list_UK = None, None
            # Check country and make list for entity resolution search if matching
            if "United States" in entities_dict[1]:
                self.list_US = self._create_different_searches(name="United States", type="country")
            if "United Kingdom" in entities_dict[1]:
                self.list_UK = self._create_different_searches(name="United Kingdom", type="country")

            print("\nEntities in the dict: ")
            print("Person: ")
            print(entities_dict[0])
            print("Info: ")
            print(entities_dict[1])
            print("-----------------------")
            # This is just for easier debugging
            # print("ERROR ON PERSONS WITH ONLY ONE NAME USED: ")

            #processed_dialogue_list = self._select_dialogue_source(entities_dict, _users, _single_logtext)  # entities_dict

            # Perform ner
            curr_userid = 0
            self.found_person_not_in_entities_dict = {}
            dialogue_list = []

            for item in _single_logtext:
                if item['type'] == 'text' and item['user']['id'] in _users:
                    if item['user']['id'] == curr_userid:
                        # Update the dialogue_list if the same speaker has used two turns
                        msg = tmp_msg + " [EOU] " + item['msg']
                        # Apply ner here
                        msg_ner = self._implement_resolution(entities_dict, msg)
                        dialogue_list[len(dialogue_list) - 1] = msg_ner
                        tmp_msg = msg
                    else:
                        msg_ner = self._implement_resolution(entities_dict, item['msg'])
                        dialogue_list.append(msg_ner)
                        # tmp_msg is used for when a speaker uses two turns (to put each of them together)
                        tmp_msg = msg_ner
                    curr_userid = item['user']['id']

                    # DEBUG
                    print(dialogue_list[len(dialogue_list) - 1])

            if self.found_person_not_in_entities_dict:
                print('\nPeople not matching from the list of given entities: ')
                print(self.found_person_not_in_entities_dict)
            print(
                ".......................................................................................................")

    def _implement_resolution(self, entities_dict, text):
        process_text = text
        person_ent_dict, info_ent_dict = entities_dict
        # Load English tokenizer, tagger, parser, NER and word vectors
        doc = self.nlp(process_text)

        #*******************************************************************************************************
        #    First perform exact string matching for movie name
        #    Then for cases of single movie name, check if movie name is a Proper noun in the sentence (using spacy) e.g. Ran
        #    If not, then check for full movie name
        #*******************************************************************************************************
        for entity, value in info_ent_dict.items():  # entity = movie_name; #value = entity_tag
            if value == 'movie#0':
                # Exact string match
                # Don't convert to lower()
                if entity in process_text:
                    process_text = re.sub(entity, value, process_text)

                '''
                # PERFROM SEARCH FOR DIFFERENT FORMS OF THE MOVIE NAME
                # Search for the various terms in the list using regex:
                for regex in self.names_list:
                    regex = regex.lower()
                    matches = re.finditer(regex, process_text.lower(), re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        match_str = str(match.group())  #match.group() gives result of match                        
                        found = process_text[match.start():match.end()]
                        process_text = re.sub(found, value, process_text)
                '''

                # ************************************************************
                # Search using spacy and ngrams for the most similar option:
                # ************************************************************
                process_text_list = process_text.split(" ")
                # remove empty strings
                process_text_list = list(filter(None, process_text_list))
                # If only one word utterance, don't perform spacy_ner
                if len(process_text_list) != 1:
                    most_similar, _percentage = self._get_max_similarity(self.names_list, process_text, type='movie')
                    # TODO:
                    # Get top two most similar strings and perform Levenshtein distance with that and the movie
                    # name to find the best result
                    # Then subsitute the most similar string
                    if _percentage >= 0.89:
                        # .lower() gives different results if removed
                        matches = re.finditer(most_similar, process_text, re.MULTILINE)
                        found = []
                        for matchNum, match in enumerate(matches, start=1):
                            # Use the index to perform substitution
                            found.append([match.start(), match.end()])
                        for index in found[::-1]:
                            process_text = process_text[:index[0]] + value + process_text[index[1]:]
                            # process_text = re.sub(most_similar, value, process_text)

                # IF MOVIE IS ONLY ONE WORD, PERFORM PRONOUN SEARCH
                if len(entity.split(' ')) == 1 and 'movie#0' not in process_text:
                    # Perform spacy on the text to get proper nouns that match movie name
                    for _word in doc:
                        if _word.pos_ in ('PROPN') and _word.text == entity:  # 'NOUN', 'PRON'
                            process_text = re.sub(entity, value, process_text)
                continue

            if value == 'budget#0':
                # Exact string match
                if entity in process_text:
                    # \\ added for regex metacharacters
                    found_match = "\\" + entity
                    process_text = re.sub(found_match, value, process_text)
                    continue

                # Further check
                # TODO:
                # edit regex for budget to include values less than 1 million
                #regex = r"\$?[0-9]{1,3}[,\s]?\d{3}[,\s]?\d{3}"
                regex = r"\$?[0-9]{1,3}[,\s]?(\d{3}[,\s]?\d{3}|\b(million)\b)"
                matches = re.finditer(regex, process_text, re.MULTILINE)
                for matchNum, match in enumerate(matches, start=1):
                    found_match = str(match.group())  # match.group() gives result of match
                    # Remove dollar sign, commas or spaces if any
                    found_match_edited = re.sub(r"[,\$\s]", '', found_match)
                    # Check if million spelt out and sub
                    if 'million' in found_match:
                        found_match_edited = re.sub('million', '000000', found_match_edited)
                    # Convert budget and then compare
                    budget_edited = re.sub(r"[,\$\s]", '', entity)
                    if found_match_edited == budget_edited:
                        if '$' == found_match[0]:
                            found_match = "\\" + found_match
                        process_text = re.sub(found_match, value, process_text)
                        continue

            if value == 'year#0':
                regex = r"\d{4}"
                matches = re.finditer(regex, process_text, re.MULTILINE)
                found = []
                for matchNum, match in enumerate(matches, start=1):
                    if int(match.group()) == entity:  # match.group() gives result of match
                        process_text = re.sub(str(match.group()), value, process_text)
                continue

            if value == 'certificate#0':
                perform_cert_resolution = False
                # use iteration to check last two dialogues
                if len(self.original_dialogue_ner) > 1:
                    it = iter(self.original_dialogue_ner[::-1])
                    for previous_utt in it:
                        next_it = next(it)
                        if 'age' in previous_utt.lower() or 'restriction' in previous_utt.lower():  # or 'certificate' in previous_utt
                            perform_cert_resolution = True
                            break
                        if 'age' in next_it.lower() or 'restriction' in next_it.lower():  # or 'certificate' in previous_utt
                            perform_cert_resolution = True
                            break
                        break   # forces iteration to only perform search for last two utterances
                # check current utterance as well
                if 'age' in process_text.lower() or 'restriction' in process_text.lower():
                    perform_cert_resolution = True
                    break

                if perform_cert_resolution:
                    #...

                    regex = r"\s\d{1,2}\s?"  # search for only the exact numbers
                    matches = re.finditer(regex, process_text, re.MULTILINE)
                    found = []
                    for matchNum, match in enumerate(matches, start=1):
                        # get position of found match and remove space if any
                        # try: if there's a space after certificate
                        if process_text[match.end()-1] == ' ':
                            found.append([match.start()+1, match.end()-1])
                        else:
                            # Check if next value is integer
                            # For cases like: cert = 16, and text = 169
                            try:
                                int(process_text[match.end()])
                                break
                            except (ValueError, IndexError):
                                # ValueError: for cases where next value is not an integer
                                # IndexError: for cases where the certificate is the last word
                                found.append([match.start() + 1, match.end()])
                    if found:
                        # start from last index due to string substitutions
                        for index in found[::-1]:
                            if process_text[index[0]:index[1]] == entity:
                                # process_text = re.sub(process_text[index[0]:index[1]], value, process_text)
                                # replace only the found indexes
                                process_text = process_text[:index[0]] + value + process_text[index[1]:]
                                #continue

            if value[0:5] == 'genre':
                if entity.lower() in process_text.lower():
                    regex = entity.lower()
                    matches = re.finditer(regex, process_text.lower(), re.MULTILINE)
                    found = []
                    for matchNum, match in enumerate(matches, start=1):
                        # get position of found match
                        try:
                            # For cases with s: e.g animations... Maybe too specific
                            # Check if next letter after genre is 's', 'ies', 'dramatic'
                            good = ['s']
                            if process_text[match.end()] in good:
                                found.append([match.start(), match.end()])
                            # For any other case such as space, '.', ...
                            else:
                                # currently this includes every mention of genre including situations like
                                # 'dramatic', ..., the option to change this is to put them in a 'bad' list
                                found.append([match.start(), match.end()])
                        except IndexError:
                            found.append([match.start(), match.end()])
                    if found:
                        for index in found[::-1]:
                            process_text = process_text[:index[0]] + value + process_text[index[1]:]
                        continue

            if value[0:7] == 'country':
                # If country not USA or UK
                if entity == 'United States':
                    for regex in self.list_US:
                        matches = re.finditer(regex, process_text, re.MULTILINE)
                        for matchNum, match in enumerate(matches, start=1):
                            # get position of found match
                            #found.append([match.start(), match.end()])
                            found = process_text[match.start():match.end()]
                            process_text = re.sub(found, value, process_text)
                elif entity == 'United Kingdom':
                    for regex in self.list_UK:
                        matches = re.finditer(regex, process_text, re.MULTILINE)
                        for matchNum, match in enumerate(matches, start=1):
                            # get position of found match
                            #found.append([match.start(), match.end()])
                            found = process_text[match.start():match.end()]
                            process_text = re.sub(found, value, process_text)
                elif entity.lower() in process_text.lower():
                    found = []
                    regex = entity.lower()
                    matches = re.finditer(regex, process_text.lower(), re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        # get position of found match
                        found.append([match.start(), match.end()])
                    if found:
                        for index in found[::-1]:
                            process_text = process_text[:index[0]] + value + process_text[index[1]:]
                        #continue

        #*************************************************
        # Method 1: Perform exact string match for persons
        #*************************************************
        for entity, value in person_ent_dict.items():  # entity = movie_name; #value = entity_tag
            # For person with 3 names
            if len(entity.split(" ")) == 3:
                entity_list = self._create_different_searches(entity, type="person")
                for regex in entity_list:
                    matches = re.finditer(regex.lower(), process_text.lower(), re.MULTILINE)
                    found = []
                    for matchNum, match in enumerate(matches, start=1):
                        # Use the index to perform substitution
                        try:
                            # Check if next letter after name is 's' , '
                            # Maybe redundant
                            good = ['s', "'"]
                            if process_text[match.end()] in good:
                                found.append([match.start(), match.end()])
                            else:
                                found.append([match.start(), match.end()])
                        except IndexError:
                            found.append([match.start(), match.end()])
                    if found:
                        for index in found[::-1]:
                            process_text = process_text[:index[0]] + value + process_text[index[1]:]
                        continue

            elif entity.lower() in process_text.lower():
                process_text = re.sub(entity, value, process_text)

        # ************************************************************
        # Spacy method 1 and ngrams for the most similar option:
        # ************************************************************
        process_text_list = process_text.split(" ")
        # remove empty strings
        process_text_list = list(filter(None, process_text_list))
        # If only one word utterance, don't perform spacy_ner
        if len(process_text_list) != 1:
            most_similar, _percentage = self._get_max_similarity(person_ent_dict, process_text, type='person')
            # TODO:
            # Get top two most similar strings and perform Levenshtein distance with that and the movie
            # name to find the best result
            # Then subsitute the most similar string
            if _percentage >= 0.89:
                # .lower() gives different results if removed
                matches = re.finditer(most_similar.lower(), process_text.lower(), re.MULTILINE)
                found = []
                for matchNum, match in enumerate(matches, start=1):
                    # Use the index to perform substitution
                    found.append([match.start(), match.end()])
                for index in found[::-1]:
                    process_text = process_text[:index[0]] + value + process_text[index[1]:]
                    # process_text = re.sub(most_similar, value, process_text)

        #********************************************
        # Spacy method 2 for further person matching
        #********************************************
        _spacy_label = ['PERSON', 'ORG']
        for ent in doc.ents:
            # NOTE: Not all persons found, so search for nouns as well.
            # Also perform exact sring search for names to be sure!
            if ent.label_ in _spacy_label:  # date, ...
                if ent.text in person_ent_dict:
                    process_text = re.sub(ent.text, person_ent_dict[ent.text], process_text)
                # If there is only one name
                elif len(ent.text.split()) == 1:
                    possibility = []
                    for entity, val in person_ent_dict.items():
                        if ent.text in str(entity):
                            possibility.append(entity)

                    if len(possibility) > 0:
                        print("-- there are {} possibilities for replacing the name {}".format(len(possibility),
                                                                                               ent.text))
                        print(possibility)
                    else:
                        print("-- there was no possibility for replacing the "
                              "name {} as it was not found in the database".format(ent.text))
                        self.found_person_not_in_entities_dict.update({ent.text: ent.label_})
                    # Substitute for the entity if only one possibility of replacing the name is found
                    if len(possibility) == 1:
                        process_text = re.sub(ent.text, person_ent_dict[possibility[0]], process_text)
                else:
                    if ent.text not in self.found_person_not_in_entities_dict:
                        self.found_person_not_in_entities_dict.update({ent.text: ent.label_})

        return process_text

    def _create_different_searches(self, name, type=None):
        _name = name

        if type == "movie":
            # FIRST DO FOR JUST MOVIES
            final_list = []
            final_list.append(_name)
            # Make it one full movie.
            if ': ' in _name:
                final_list.append(re.sub(':', '', _name))  # [Avengers Infinity War]
            else:
                final_list.append(re.sub(':', ' ', _name))  # [Avengers Infinity War]
            # Split by ':' and input full name
            diff_names = _name.split(":")
            # Reverse input order so the entity search is first performed the last name
            for x in diff_names[::-1]:  # ['Infinity War', 'Avengers']
                final_list.append(x)

            '''
            abbr1 = ""
            abbr2 = ""        
    
            # Abbreviations e.g AIW for Avengers: Infinity War
            # Search for space after ':' and remove
            if ': ' in _name:
                index = _name.find(':')
            char_ = list(name)
            if char_[index+1] == ' ':
                char_.pop(index+1)        
            _name = "".join(char_)
    
            # Split to get abbreviations e.g AIW for Avengers: Infinity War
            for nm_ in diff_names:    
                split_name = nm_.split(' ')   #['Avengers']
                                                #['Infinity', 'War']
                for name_together in split_name:
                    abbr1 += name_together[0]   
    
                if len(split_name) > 2: # e.g: ['Lord', 'of', 'the', 'rings']
                    for name_seperate in split_name:
                        abbr2 += name_seperate[0]   
    
            # Only append abbreviations greater than 2 for now
            #if len(abbr1) > 2:  
                #final_list.append(abbr1)    # AIW (after for loop)
            #if len(abbr2) > 2: # e.g: ['Lord', 'of', 'the', 'rings']
                #final_list.append(abbr2)    # LOTR (after for loop)
            '''
            return final_list

        if type == "country":
            if _name == "United States":
                return ["United States", "USA", "U.S.A.", "US"]
            if _name == "United Kingdom":
                return ["United Kingdom", "UK", "U.K."]

        if type == "person":
            _name_list = _name.split(" ") # ['Paul', 'Thomas', 'Anderson']
            name_0_2 = _name_list[0] + " " + _name_list[2]  # ['Paul Anderson']
            name_1_2 = _name_list[1] + " " + _name_list[2]  # ['Thomas Anderson']
            name_0_1 = _name_list[0] + " " + _name_list[1]  # ['Paul Thomas']
            return  [_name, name_0_2, name_1_2, name_0_1]

    def _get_max_similarity(self, names_list, sentence, type=None):
        result_dict = {}
        sim_dict2 = {}

        #if type=='person':
        #    names_list = [x for x in names_list]

        # name_list is used for cases where ":" is in movie name so multiple names created
        for mv in names_list:
            similarity_dict = {}
            # Tokenize 1: regex
            # movie_toknzd = re.findall(r"\w+", mv.lower())

            # Tokenize 2: spacy
            doc = self.nlp(mv)
            movie_toknzd = []
            for token in doc:
                movie_toknzd.append(token.text)
            # if len movie name longer than 2, perform multiple ngrams
            if len(movie_toknzd) > 2:
                _xrange = 3
                _yrange = len(movie_toknzd) + 1
            else:
                _xrange = len(movie_toknzd)
                _yrange = len(movie_toknzd) + 1

            for n in range(_xrange, _yrange):
                ngram_result = self.ngrams_sentence(sentence, n)
                #movie_joined = mv #" ".join(movie_toknzd)
                # Check similarity of the movie and the ngrammed phrase
                #for mov in movie_joined:

                if type=='person':
                    doc1 = self.nlp(mv.lower())
                elif type=='movie':
                    doc1 = self.nlp(mv)

                for phrase in ngram_result:
                    if type == 'person':
                        doc2 = self.nlp(phrase.lower())
                    elif type == 'movie':
                        doc2 = self.nlp(phrase)
                    #doc2 = self.nlp(phrase.lower())
                    similarity = doc1.similarity(doc2)
                    similarity_dict.update({similarity: phrase})
                    #sim_dict2.update({similarity: phrase})
                    # print(doc1.text, ",", doc2.text, "---> Similarity: ", similarity)

            if similarity_dict:
                single_max_result = max(key for key in similarity_dict.keys())
                result_dict.update({similarity_dict[single_max_result]: single_max_result})

        # Get the most likely possibility
        if result_dict:
            # if all max are = 1, get the most likely
            tmp_prob = 0
            same = False
            for prob in result_dict.values():
                if prob == tmp_prob:
                    same = True
                tmp_prob = prob
            if same is True:
                curr_len = 0
                for single in result_dict:
                    if len(single) > curr_len:
                        single_max = single
                        curr_len = len(single)
                return single_max, result_dict[single_max]
            else:
                best_possibility = max(key for key in similarity_dict.keys())
                return similarity_dict[best_possibility], best_possibility
        else:
            return "No similarity", 0.0

    def ngrams_sentence(self, sent, n):
        s = sent.lower()
        # Tokenize 1:
        # Replace all non alphanumeric characters with spaces
        # s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
        # Break sentence into token, remove empty tokens
        # tokens = [token for token in s.split(" ") if token != ""]
        # Concatenate tokens and use the zip function to help generate n-grams

        # Tokenize 2: Using spacy
        doc = self.nlp(sent)
        tokens = []
        for token in doc:
            tokens.append(token.text)

        sequence = [tokens[i:] for i in range(n)]
        # The zip function takes the sequences as a list of inputs (using the * operator,
        ngrams = zip(*sequence)
        return [" ".join(ngram) for ngram in ngrams]

    def _create_final_entity_dict(self, dialogue, entities_dict):
        # TODO:
        # After processing the dialogue, use the entities found to create a new dict
        # e.g. if actor#4 and actor#7 in the dialogue, make a new dict to change it to
        # actor#0 and actor#1 instead

        # Note: applicable for other multiple entities such as country, genre
        return

if __name__ == "__main__":
    import reader as rdr
    from libs.moviedatalib import DataMovie, DataPerson, Trivia

    path_logs = "../logfiles/"
    mturk_session = "moviedatagen_real_test_2/"  # "versuchsreihe3/"
    path_data = "./movies/data.pkl"

    ner = NamedEntityResolution(path_logs, mturk_session, path_data)
    # ner = NamedEntityResolution(path_logs="", mturk_session=mturk_session)
    # ner.run("")

    # ner.run()
