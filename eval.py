from collections import defaultdict

import yaml
import pickle

GHOSTERY_DATA_FILE_PATH = "ghostery.csv"
FIREFOX_DATA_FILE_PATH = "firefox.csv"
PRIVACY_BADGER_DATA_FILE_PATH = "privacy_badger.csv"
UBLOCK_FILE_PATH = "ublock.csv"

'''
Takes a comma separated file of websites and observed trackers in the form of:

Google.com,adservice.google.com/
Youtube.com,static.doubleclick.net/
Amazon.com,aax-us-east.amazon-adsystem.com/,c.amazon-adsystem.com/,s.amazon-adystem.com/

where the first website is the origin domain (i.e. the website from the Alexa top 50 websites)
and all the URLs that follow are the observed trackers found on that website
'''

class Evaluator():
    def __init__(self):
        # Blocker specific results i.e. Ghostery -> {Google.com -> adservice.google.com/, Youtube.com -> static.doubleclick.net/ ...}
        self.blocker_results = {}

        # Map from origin website to all trackers ever observed on page i.e. Google.com -> adservice.google.com/
        self.website_trackers = defaultdict(set)

        # Maps each tracker observed to the frequency it appears across all domains
        self.tracker_frequency = defaultdict(lambda: 0)

        # Maps each website to their corresponding Alexa top 50 rank
        self.websites = {}

        self.eval_func = evaluation_function

    def process_data(self, data_file_path, blocker_name):
        results = defaultdict(set)
        with open(data_file_path) as f:
            for rank, line in enumerate(f, start=1):
                
                split = line.split(",")
                origin_domain = split[0]
                
                if origin_domain not in self.websites:
                    self.websites[origin_domain] = rank
                else:
                    assert self.websites[origin_domain] == rank

                for tracker in split[1:]:
                    if tracker == '' or tracker == '\n':
                        continue # break?
                    # Only update the frequency of this observed tracker if we have not observed it on this domain before
                    if tracker not in self.website_trackers[origin_domain]:
                        self.tracker_frequency[tracker] += 1
                        self.website_trackers[origin_domain].add(tracker)

                    results[origin_domain].add(tracker)

        self.blocker_results[blocker_name] = results

    def get_frequency(self, tracker_name):
        return self.tracker_frequency[tracker_name]

    def blocker_score(self, blocker_name):
        return self.blocker_subset_score(blocker_name, self.websites.keys())

    def blocker_subset_score(self, blocker_name, subset):
        blocked_trackers = self.blocker_results[blocker_name]

        score = 0

        for origin_domain in blocked_trackers:
            if origin_domain in subset:
                rank = self.websites[origin_domain]

                for tracker in blocked_trackers[origin_domain]:
                    score += self.eval_func(rank, self.tracker_frequency[tracker])

        return score

    def set_evaluation_function(self, evaluation_function):
        self.eval_func = evaluation_function

    def save_website_trackers_to_pickle(self, file_name):
        with open(file_name, 'wb') as handle:
            print("Saving website and tracker info into {}".format(file_name))
            pickle.dump(self.website_trackers, handle, protocol=pickle.HIGHEST_PROTOCOL)

'''
Evaluation function used to evaluate each particular blocker

Take the inverse of the website rank (squared) multiplied by the frequency of the tracker observed on websites
Higher scores represent a superior blocker (because a higher scores suggests that it blocks more prevalent/frequent
trackers on more prominent websites)

Using the inverse of the website rank square reduces the value of obscure trackers (i.e. with frequency 1) found on less
prominent websites - this was the case for both Firefox and Privacy Badger which ended up getting very good scores because
they simply blocked more trackers with frequency 1 found on less prominent websites which suggests that these blockers
are better at blocking the "long tail of trackers" on the internet while Ghostery is better at blocking the biggest trackers
Run the analysis with alt_evaluation_function for more information
'''
def evaluation_function(rank, tracker_frequency):
    return ((1 / rank) ** 2) * tracker_frequency

def alt_evaluation_function(rank, tracker_frequency):
    return (1 / rank) * tracker_frequency

if __name__ == '__main__':
    eval = Evaluator()

    eval.process_data(GHOSTERY_DATA_FILE_PATH, "Ghostery")
    eval.process_data(FIREFOX_DATA_FILE_PATH, "Firefox")
    eval.process_data(PRIVACY_BADGER_DATA_FILE_PATH, "PrivacyBadger")
    eval.process_data(UBLOCK_FILE_PATH, "uBlock")

    # UNCOMMENT THIS LINE TO SEE EVALUATION FUNCTION THAT PLACES HIGHER IMPORTANCE ON BLOCKING OBSCURE TRACKERS
    # eval.set_evaluation_function(alt_evaluation_function)

    print("Blockers\tGhostery\tFirefox\t\tPrivacyBadger\tuBlock")
    print("All websites\t{:.3f}\t\t{:.3f}\t\t{:.3f}\t{:.3f}".format(eval.blocker_score("Ghostery"),
                                                             eval.blocker_score("Firefox"),
                                                             eval.blocker_score("PrivacyBadger"),
                                                             eval.blocker_score("uBlock")))
    
    # To evaluate each blocker on a subset of the collected websites, simply create a subset of websites that should be
    # considered i.e. subset = set(); subset.add(NEWS_WEBSITE); ... and call eval.blocker_subset_score("Ghostery", subset) etc.

    with open('website_by_type.yaml', 'r') as stream:
        website_by_type = yaml.safe_load(stream)
    for site_category in website_by_type.keys():
        subset = set(website_by_type[site_category])
        if (len(site_category) < 5):
            site_category = site_category + "\t"
        print("{}\t{:.3f}\t\t{:.3f}\t\t{:.3f}\t{:.3f}".format(
            site_category,
            eval.blocker_subset_score("Ghostery", subset),
            eval.blocker_subset_score("Firefox", subset),
            eval.blocker_subset_score("PrivacyBadger", subset),
            eval.blocker_subset_score("uBlock", subset)))

    # Uncomment this line to save each website and its corresponding tracker informaiton into a pickle file
    # eval.save_website_trackers_to_pickle('web2tracker.pkl')




