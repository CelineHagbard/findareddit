SUBREDDIT_NAME = "findareddit"
# Username to send list to. Omit the /u/ or /user/
PM_TO = ''
# List of wiki pages to exclude in search
DIRECTORY_WIKIS = ['directory', '/r/sfwpornnetwork/wiki/network']
# Name of wiki page to store new subs that are found.
NEWSUBS_WIKI = 'newsubs'
# if True, loads list of subs from NEWSUBS_WIKI
CHECK_NEWSUBS = True 
# if True, saves list of extracted subs to NEWSUBS_WIKI
SAVE_NEWSUBS = True 
# time in seconds
SLEEP_TIME = 60 * 60 * 12
# inital time to sleep if uncaught exceptions
ERROR_SLEEP =  30
PM_SUBJECT = 'Found new Subreddits!'
PM_STRING = '''I found {} subreddits mentioned in the last 24 hours that aren't in the directory:

* {}
'''