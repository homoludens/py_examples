# -*- coding: utf-8 -*-

"""
Klient Google Readera
"""

# Mocno inspirowane (z kopiowaniem sporych fragmentów kodu włącznie):
# http://blog.gpowered.net/2007/08/google-reader-api-functions.html
#
# Kluczowe informacje:
# http://code.google.com/p/pyrfeed/wiki/GoogleReaderAPI

import urllib
import urllib2
import re
try:
        import simplejson as json
except ImportError:
        import json
import time
from lxml import etree, objectify

import logging
log = logging.getLogger("reader")

TOKEN_VALID_TIME = 60
#DUMP_REQUESTS = True
#DUMP_REQUESTS = False
#DUMP_REPLIES = False
#DUMP_REPLIES = True

class GoogleLoginFailed(Exception):
    pass
class GoogleOperationFailed(Exception):
    pass

#SOURCE = 'my-small-script'
SOURCE = 'mekk'

GOOGLE_URL = 'http://www.google.com'
READER_URL = GOOGLE_URL + '/reader'
LOGIN_URL = 'https://www.google.com/accounts/ClientLogin'
TOKEN_URL = READER_URL + '/api/0/token'
TAG_LIST_URL = READER_URL + '/api/0/tag/list'
PREFERENCE_LIST_URL = READER_URL + '/api/0/preference/list'
UNREAD_COUNT_URL = READER_URL + '/api/0/unread-count'
SUBSCRIPTION_LIST_URL = READER_URL + '/api/0/subscription/list'
SUBSCRIPTION_EDIT_URL = READER_URL + '/api/0/subscription/edit'
TAG_EDIT_URL = READER_URL + '/api/0/edit-tag'
TAG_DISABLE_URL = READER_URL + '/api/0/disable-tag'
IN_STATE_URL = READER_URL + '/atom/user/-/state/com.google/%s'
GET_FEED_URL = READER_URL + '/atom/feed/'
READING_TAG_URL = READER_URL + '/atom/%s'

class GoogleReaderClient(object):

    """
    Selected GoogleReader functions. Connects to specified Google Account
    and retrieves/modifies GoogleReader subscriptions.

    The get_*_atom functions retrieve different articles as Atom feeds.
    Apart from specific parameters, all those functions handle the following
    args:

    - count         - how many elements to get (by default Google default, i.e. 20)
    - continue_from - value of gr:continuation in "previous" call, to implement paging
    - older_first=True - start from older items, not from newest

    Remaining functions allow one to manage subscription feeds.
    """
    
    def __init__(self, login, password):
        self.session_id = self._get_session_id(login, password)
        self.cached_token = None
        self.cached_token_time = 0
        self.my_id = '-'
        self.cached_feed_item_ids = dict()

    ############################################################
    # Small utilities, used mainly internally

    def tag_id(self, tag):
        """
        Converts tag name (say "Życie: Polityka" into 
        tag id (say "user/-/label/Życie: Polityka").
        
        If parameter is already in this form, leaves it as-is
        """
        if not tag.startswith('user/'):
            tag = 'user/%s/label/%s' % (self.get_my_id(), tag)
        return tag

    def get_my_id(self):
        if self.my_id == '-':
            tl = self.get_tag_list()
            for vl in tl['tags']:
                m = re.match('user/(\d+)/', vl['id'])
                if m:
                    self.my_id = m.group(1)
                    break
        return self.my_id

    def feed_item_id(self, feed):
        """
        Returns identifier of the first item of given tag feed.
        Used during sub/unsubscription (for some reason it is needed)
        """
        i = self.cached_feed_item_ids.get(feed)
        if not i:
            r = self.get_feed_atom(feed, count = 2, format = 'obj')
            i = str(r.entry.id)
            self.cached_feed_item_ids[feed] = i
        return i

    ############################################################
    # Public API - atom feeds (articles)

    def get_feed_atom(self, url, **kwargs):
        """
        Atom feed for any feed. Works also for unsubscribed feeds
        """
        return self._get_atom(GET_FEED_URL + url,
                              **kwargs)

    def get_reading_list_atom(self, **kwargs):
        """
        Atom feed of unread items
        """
        return self.get_instate_atom('reading-list', **kwargs)

    def get_read_atom(self, **kwargs):
        """
        Atom feed of (recent) read items
        """
        return self.get_instate_atom('read', **kwargs)

    def get_tagged_atom(self, tag, **kwargs):
        """
        Atom feed of (unread?) items for given tag
        """
        tagged_url = READING_TAG_URL % self.tag_id(tag)
        return self._get_atom(tagged_url, **kwargs)

    def get_starred_atom(self, **kwargs):
        """
        Atom feed of starred items
        """
        return self.get_instate_atom('starred', **kwargs)

    def get_fresh_atom(self, **kwargs):
        """
        Atom feed of fresh (newly added) items
        """
        return self.get_instate_atom('fresh', **kwargs)

    def get_broadcast_atom(self, **kwargs):
        """
        Atom feed of public (shared) items
        """
        return self.get_instate_atom('broadcast', **kwargs)

    def get_instate_atom(self, state, **kwargs):
        """
        Atom feed of items in any state. Known states:

        read, kept-unread, fresh, starred, broadcast (public items),
        reading-list (all), tracking-body-link-used, tracking-emailed,
        tracking-item-link-used, tracking-kept-unread

        get_fresh_atom is equivalent to get_instate_atom('fresh') and so on.
        """
        return self._get_atom(IN_STATE_URL % 'state', **kwargs)


    ############################################################
    # Public API - subscription info

    def get_subscription_list(self, format = 'obj'):
        """
        Returns info about all subscribed feeds.

        If format = 'xml' returns bare XML text

        If format = 'json', returns bare JSON text

        If format = 'obj', returns parsed JSON (python dictionary)
        """
        return self._get_list(SUBSCRIPTION_LIST_URL, format)

    def get_tag_list(self, format = 'obj'):
        return self._get_list(TAG_LIST_URL, format)

    def get_preference_list(self, format = 'obj'):
        return self._get_list(PREFERENCE_LIST_URL, format)

    def get_unread_count(self, format = 'obj'):
        return self._get_list(UNREAD_COUNT_URL, format)

    ############################################################
    # Public API - subscription modifications

    def subscribe_feed(self, feed_url, title = None):
        """
        Subscribe to given feed. Optionally set title
        """
        return self._change_feed(feed_url, 'subscribe', title = title)

    def unsubscribe_feed(self, feed_url):
        """
        Unsubscribe from the given feed.
        """
        return self._change_feed(feed_url, 'unsubscribe')

    def change_feed_title(self, feed_url, title):
        """
        Changes the feed title
        """
        return self._change_feed(feed_url, 'edit', title = title)

    def add_feed_tag(self, feed_url, title, tag):
        """
        Adds feed to new tag (folder).
        Tag can be specified either as full id copied from the tag list
        (say "user/04686467480557924617/label/\u017bycie: Polityka")
        or as the sole name ("Życie: Polityka")
        
        It seems that tag may be new (not-yet-existant tags do work)
        """
        return self._change_tag(feed_url, title, add_tag = tag)

    def remove_feed_tag(self, feed_url, title, tag):
        """
        Removes feed from given tag (folder).
        Tag can be specified either as full id copied from the tag list
        (say "user/04686467480557924617/label/\u017bycie: Polityka")
        or as the sole name ("Życie: Polityka")
        """
        return self._change_tag(feed_url, title, remove_tag = tag)

    def disable_tag(self, tag):
        """
        Removes tag as a whole
        """
        url = TAG_DISABLE_URL +  '?client=%s' % SOURCE
        post_data = {
            's' : self.tag_id(tag),
            'ac' : 'disable-tags',
            }
        reply = self._make_call(url, post_data)
        if reply != "OK":
            raise GoogleOperationFailed
        return

    ############################################################
    # Helper functions

    def _get_session_id(self, login, password):
        """
        Logging in (and obtaining the session id)
        """
        header = {'User-agent' : SOURCE}
        post_params = {
            'Email': login,
            'Passwd': password,
            'service': 'reader',
            'source': SOURCE,
            'continue': GOOGLE_URL, 
            }
        post_data = urllib.urlencode(post_params) 
        request = urllib2.Request(LOGIN_URL, post_data, header)

        if log.isEnabledFor("info"):
            pdcopy = post_params.copy()
            pdcopy['Passwd'] = '*******'
            log.info("Calling %s with parameters:\n    %s" % (
                        request.get_full_url(), str(pdcopy)))

        try:
            f = urllib2.urlopen( request )
        except urllib2.HTTPError, e:
            if e.code == 403:
                raise GoogleLoginFailed
            else:
                raise
        result = f.read()

        log.debug("Result: %s" % result)

        sid = re.search('Auth=(\S*)', result).group(1)
        if not sid:
            raise GoogleLoginFailed
        return sid

    def _get_token(self):
        """
        Obtain the call protection token
        """
        # Token jest jakiś czas ważny...
        t = time.time()
        if t - self.cached_token_time > TOKEN_VALID_TIME:
            self.cached_token = self._make_call(TOKEN_URL)
            self.cached_token_time = t
        return self.cached_token

    def _get_atom(self, url, count = None, older_first = False, continue_from = None, format = 'obj'):
        """
        Actually get ATOM feed. url is base url (one of the state or label urls).
        count is the articles count (default 20), ordering_back set to False means older
        first, continue_from can be set to gr:continuation value from the feed to
        grab more items

        format can be 'xml' (raw xml text), 'etree' (lxml.etree) or 'obj'
        (lxml.objectify - default)
        """
        args = {}
        if count is not None:
            args['n'] = "%d" % count
        if older_first:
            args['r'] = 'o'
        if continue_from:
            args['c'] = continue_from
        if args:
            url = url.encode('utf-8') + '?' + urllib.urlencode(args)
        r = self._make_call(url)
        if format == "obj":
            return objectify.fromstring(r)
        elif format == "etree":
            return etree.XML(r)
        else:
            return r

    def _change_feed(self, feed_url, operation, title = None, add_tag = None, remove_tag = None):
        """
        Subscribe or unsubscribe
        """
        url = SUBSCRIPTION_EDIT_URL + '?client=%s' % SOURCE
        post_data = { 
            'ac' : operation,
            's' : "feed/" + feed_url,
            'T' : self._get_token(),
            }
        if title:
            post_data['t'] = title
        if add_tag:
            post_data['a'] = self.tag_id(add_tag)
        if remove_tag:
            post_data['r'] = self.tag_id(remove_tag)
        reply = self._make_call(url, post_data)
        if reply != "OK":
            raise GoogleOperationFailed
        return

    def _change_tag(self, feed_url, title, add_tag = None, remove_tag = None):
        """
        Subscribe or unsubscribe
        """
        #url = TAG_EDIT_URL + '?client=%s' % SOURCE
        url = SUBSCRIPTION_EDIT_URL + '?client=%s' % SOURCE
        post_data = { 
            'ac' : 'edit',
            's' : "feed/" + feed_url,
            't' : title,
            'T' : self._get_token(),
            }
        if add_tag:
            post_data['a'] = self.tag_id(add_tag)
        if remove_tag:
            post_data['r'] = self.tag_id(remove_tag)
        reply = self._make_call(url, post_data)
        if reply != "OK":
            raise GoogleOperationFailed

        # # It is likely refresh, don't work so ...
#         url = TAG_EDIT_URL + '?client=%s' % SOURCE
#         post_data = {
#             'a' : 'user/%s/state/com.google/read' % self.get_my_id(),
#             'async' : 'true',
#             'i' : self.feed_item_id(feed_url),
#             's' : "feed/" + feed_url,
#             }
#         reply = self._make_call(url, post_data)
#         if reply != "OK":
#             raise GoogleOperationFailed

        return

    def _get_list(self, url, format):
        if format == 'obj':
            return simplejson.loads(
                self._make_call(url + '?output=json'))
        else:
            return self._make_call(url + '?output=' + format)
        

    def _make_call(self, url, post_data=None):
        header = {'User-agent' : SOURCE}
        header['Authorization'] = 'GoogleLogin auth=%s' % self.session_id
        if post_data is not None:
            true_data = [ (key, value.encode('utf-8')) for key, value in post_data.iteritems() ]
            true_data = urllib.urlencode(true_data)
        else:
            true_data = None
        request = urllib2.Request(url.encode('utf-8'), true_data, header)

        if log.isEnabledFor("info"):
            if post_data:
                log.info("Calling %s with parameters:\n    %s" % (
                        request.get_full_url(), str(post_data)))
            else:
                log.info("Calling %s" % request.get_full_url())

        f = urllib2.urlopen( request )
        result = f.read()

        log.debug("Result: %s" % result)

        return result

