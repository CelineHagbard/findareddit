import praw, re
from datetime import timedelta, datetime
from time import sleep
from prawcore.exceptions import NotFound, Redirect, BadRequest, Forbidden, RequestException
from constants import *

wiki_regex = re.compile(r'/?r/([A-Za-z0-9_]+)[^A-Za-z0-9_]')
dir_regex = re.compile(r'/?(r/([A-Za-z0-9_]+)/wiki/)?([A-Za-z0-9_/]+)')


def send_pm(reddit, pm_subreddits):
    """ Sends the PM to the listed user
    """
    subs_text = '\n\n* '.join(("/r/" + sub for sub in pm_subreddits))
    pm_text = PM_STRING.format(len(pm_subreddits), subs_text)
    print(pm_text)
    user = reddit.redditor(PM_TO)
    user.message(PM_SUBJECT, pm_text)
    print("Sending message to /u/{}".format(PM_TO))


def save_new_subs(reddit, subreddit, pm_subreddits):
    """ Saves a list of the subs found in this run to the NEWSUBS_WIKI wiki page
    """
    lines = []
    try:
        wiki_text = subreddit.wiki[NEWSUBS_WIKI].content_md
    except NotFound:
        print("New Subs wiki not found. Not saving to wiki.")
        return

    for subname in pm_subreddits:
        line = "/r/{}|||{}".format(subname, pm_subreddits[subname][0])
        lines.append(line)

    now = datetime.utcnow().isoformat()
    new_wiki_text = wiki_text.rstrip() \
            + "\n\n{}\n\nSubreddit|||Description\n---|---|---|---\n".format(now)
    subs_text = '\n'.join(lines)
    new_wiki_text += subs_text

    try:
        subreddit.wiki[NEWSUBS_WIKI].edit(new_wiki_text)
    except:
        print("Error writing to new subs wiki")
        return False
    print("Saving data to {}".format(NEWSUBS_WIKI))


def get_wiki_subreddits(reddit, subreddit):
    """ Builds a set() of subreddit names based on names found in 
        DIRECTORY_WIKI and NEWSUBS_WIKI if the contant CHECK_NEWSUBS == True
    """

    dir_subreddits = set()
    for wiki_name in DIRECTORY_WIKIS + [NEWSUBS_WIKI]:
        match = dir_regex.match(wiki_name)
        if match:
            try:
                if match.group(2):
                    wiki_text = reddit.subreddit(match.group(2)) \
                                       .wiki[match.group(3)].content_md
                else:
                    wiki_text = subreddit.wiki[match.group(3)].content_md
                matches = wiki_regex.findall(wiki_text)
                dir_subreddits.update(m.lower() for m in matches)
                print("Added subs from {}. Total excluded subs: {} "
                            .format(wiki_name, len(dir_subreddits)))
            except NotFound:
                print('Wiki page {} was not found.'.format(wiki_name))
        else:
            print("Wiki page '{}' does not appear to be valid syntax."
                                                .format(wiki_name))

    return dir_subreddits 


def scan_post(reddit, post, dir_subreddits = set(), pm_subreddits = dict()):
    """ Scans the text of comments in a post for subreddit names which are not
    in 'dir_subreddits', adds them to the set 'pm_subreddits', and returns it.
    """
    print('\nPost "{}", {}'.format(post.title, 
                datetime.utcfromtimestamp(post.created_utc).isoformat()))
    post.comments.replace_more(limit=None)
    comments_text = " ".join((c.body for c in post.comments.list()))
    #print (comments_text)
    matches = matches = wiki_regex.findall(comments_text)
    subreddits = set(m.lower() for m in matches)

    for subname in subreddits:
        if subname in dir_subreddits:
            print("    /r/{} already in directory".format(subname))
            continue
        if subname in pm_subreddits:
            print("    /r/{} already found this scan".format(subname))
            continue
        try:
            sub = reddit.subreddit(subname)
            if sub.subreddit_type != 'public':
                print("    /r/{} is not public".format(subname))
                continue
            elif sub.quarantine:
                print("    /r/{} is quarantined".format(subname))
                continue
            else:
                pm_subreddits[subname] = (sub.public_description.replace('\n',' '),)
                print(" +  Adding /r/{} to PM list".format(subname))
        except (NotFound, Redirect):
            print("    /r/{} is not found.".format(subname))
            continue
        except Forbidden:
            print("    /r/{} is not public".format(subname))
        except BadRequest:
            print("Bad Request for sub: '/r/{}'." +
                "Please contact /u/CelineHagbard with a stack trace".format(subname))
        

    return pm_subreddits


def scan_sub(reddit, subreddit):
    """ Scans the posts in the last 24 hours
        Returns set pm_subreddits containing subreddit names found in the scan
    """
    posts = []
    pm_subreddits = dict()
    dir_subreddits = get_wiki_subreddits(reddit, subreddit)
    date_cutoff = datetime.utcnow() - timedelta(days=1)
    after = None
    # Fetch up to 1000 posts, 100 each request, up to 24 hours ago
    for _ in range(10):
        posts += list(subreddit.new(limit = 100, params={'after':after}))
        if datetime.utcfromtimestamp(posts[-1].created_utc) < date_cutoff:
            break
        else:
            after = posts[-1].fullname
    # Iterate over each post that's less than 24 hours old
    print("Retrieved {} posts".format(len(posts)))
    for post in posts:
        if datetime.utcfromtimestamp(post.created_utc) < date_cutoff:
            break
        pm_subreddits.update(scan_post(reddit, post, dir_subreddits, pm_subreddits))

    return pm_subreddits


def authenticate():
    reddit = praw.Reddit("findaredditdirectory")
    try:
        print("Logged in as {}".format(reddit.user.me().name))
    except Exception as e:
        print (type(e))
        print("Error logging in. Exiting program")
        return

    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    return reddit, subreddit


def main():
    reddit, subreddit = authenticate()
    failed_attempts = 0
    while True:
        try:
            print("Beginning loop\n\n")
            pm_subreddits = scan_sub(reddit, subreddit)
            send_pm(reddit, pm_subreddits)
            if SAVE_NEWSUBS:
                save_new_subs(reddit, subreddit, pm_subreddits)
            print ("Sleeping for 12 hours...\n")
            sleep(SLEEP_TIME)
            
            failed_attempts = 0
        except RequestException as e:
            print (type(e))
            if failed_attempts > 5:
                print("Script encountered more than 5 uncaught errors without a successful run")
                print("Exiting program")
                raise e
                return
            failed_attempts += 1
            error_sleep = ERROR_SLEEP * failed_attempts
            print("Error. Sleeping {} seconds and trying again".format(error_sleep))
            sleep(error_sleep)
            


if __name__ == "__main__":
    main()







