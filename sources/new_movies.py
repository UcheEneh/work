from imdb import IMDb
import re
import os
import pickle
from tqdm import tqdm

class NewMovies:
    def __init__(self, path, txt):
        self.path_txt = os.path.join(path, txt)
        self.path_out = path

    def generate_movie_info_dict(self):
        # Goes through all movies and save relevant movies in a dict.
        imdb = IMDb()
        movie_list_dict = []

        with open(self.path_txt, 'r') as f:
            contents = f.readlines()

        print("process content.")
        mid_list = []
        for item in tqdm(contents):
            mid_list.append(re.sub('tt', '', str(item)))
        print("Finished.")

        print("Generate movie dict list ...")
        idx = 0  # save every 20 movie.
        for mid in tqdm(mid_list):
            try:
                movie = imdb.get_movie(mid)
            except Exception as e:
                print(e)
                continue

            if 'top 250 rank' in movie.data:
                continue

            if 'languages' not in movie.data:
                continue

            if 'rating' not in movie.data:
                continue

            if 'votes' not in movie.data:
                continue

            if 'kind' not in movie.data:
                continue

            if int(movie.data['year']) < 1990:
                continue

            if float(movie.data['rating']) < 7.0:
                continue

            movie_list_dict.append({
                'movie': str(movie),
                'id': int(mid),
                'year': movie.data['year'],
                'rating': movie.data['rating'],
                'votes': movie.data['votes'],
                'kind': movie.data['kind']
            })

            if (idx % 20) == 0:
                self._save_pkl(file=movie_list_dict, path="../movies/movie_dict_list.pkl")
            idx += 1
        print("Finished.")

    def read_movie_info_dict(self):
        with open("../movies/movie_dict_list.pkl", 'rb') as f:
            movies = pickle.load(f)

        movie_votes5000 = []
        movie_votes10000 = []
        movie_votes15000 = []

        for movie in movies:
            if movie['votes'] >= 5000:
                movie_votes5000.append(movie)
            if movie['votes'] >= 10000:
                movie_votes10000.append(movie)
            if movie['votes'] >= 15000:
                movie_votes15000.append(movie)

        with open("../movies/movies_votes15000.pkl", 'wb') as f:
            pickle.dump(movie_votes15000, f)

        stop = "here"

    def run(self):
        imdb = IMDb()
        list_id = []
        list_non_english = []
        self.list_good_movies = []

        with open(self.path_txt, 'r') as f:
            contents = f.readlines()
        # run through a certain number of movie ids in the list
        for x in contents[0:100]:  # e.g: first 100
            x = str(x)
            x = re.sub('tt', '', x)
            list_id.append(x)
        
        count = 0
        for _id in list_id:  
            count = count + 1
            try:
                movie = imdb.get_movie(_id)
            except Exception as e:
                print(e)
            else:
                bad_data = False
                if 'top 250 rank' in movie.data or 'languages' not in movie.data or 'rating' not in movie.data:
                    continue        
                elif movie.data['languages'][0] != 'English':
                    bad_data = True
                    list_non_english.append(_id)
                if int(movie.data['year']) < 1980 or float(movie.data['rating']) < 7.0:
                    continue
                if bad_data == False:
                    self.list_good_movies.append(movie.data['title'])
                    #DEBUG
                    print(count, "/ {}".format(len(list_id)))   
        print("DONE")
        self._save(self.list_good_movies)

    def _save(self, list):
        fname = 'good movies.txt'
        with open(os.path.join(self.path_out, fname), 'w') as f:
            for item in list:
                f.write("%s\n" % item)
            print(len(self.list_good_movies), "good movies saved into '{}'".format(self.path_out + fname))

    def _save_pkl(self, file, path):
        with open(path, 'wb') as f:
            print("Saving ...")
            pickle.dump(file, f)
            print("Saved.")


if __name__ == '__main__':
    path = '../movies/'
    txt = 'full movies list.txt'    
    nm = NewMovies(path=path, txt=txt)
    nm.read_movie_info_dict()
    # nm.generate_movie_info_dict()

