from framework.mongo import db
from framework.search import Keyword

from framework import StoredObject, fields, storage, Q

import datetime

class User(StoredObject):
    _id = fields.StringField(primary=True)

    username = fields.StringField()
    password = fields.StringField()
    fullname = fields.StringField()
    is_registered = fields.BooleanField()
    is_claimed = fields.BooleanField()
    verification_key = fields.StringField()
    emails = fields.StringField(list=True)
    email_verifications = fields.DictionaryField()
    aka = fields.StringField(list=True)
    date_registered = fields.DateTimeField()#auto_now_add=True)

    keywords = fields.ForeignField('keyword', list=True, backref='keyworded')

    _meta = {'optimistic' : True}

    @property
    def surname(self):
        """
        The user's preferred surname or family name, as they would prefer it to
        appear in print.
        e.g.: "Jeffrey Spies" would be "Spies".
        """
        # TODO: Give users the ability to specify this via their profile
        return self.fullname.split(' ')[-1]

    @property
    def given_name(self):
        """
        The user's preferred given name, as they would be addressed personally.
        e.g.: "Jeffrey Spies" would be "Jeffrey" (or "Jeff")
        """
        # TODO: Give users the ability to specify this via their profile
        return self.fullname.split(' ')[0]

    @property
    def given_name_initial(self):
        """
        The user's preferred initialization of their given name.

        Some users with common names may choose to distinguish themselves from
        their colleagues in this way. For instance, there could be two
        well-known researchers in a single field named "Robert Walker".
        "Walker, R" could then refer to either of them. "Walker, R.H." could
        provide easy disambiguation.

        NOTE: The internal representation for this should never end with a
              period. "R" and "R.H" would be correct in the prior case, but
              "R.H." would not.
        """
        #TODO: Give users the ability to specify this via their profile.
        return self.given_name[0]

    @classmethod
    def search(cls, terms):
        keywords = terms.lower().split(' ')
        if terms.lower() not in keywords:
            keywords.append(terms.lower())
        
        o = []
        for i in xrange(len(keywords)):
            o.append([])

        results = cls.find(Q('keywords', 'in', keywords))
        keyword_set = set(keywords)

        for result in results:
            result_set = set([kwd._id for kwd in result.keywords])
            intersection = result_set.intersection(keyword_set)
            o[len(o)-len(intersection)].append(result)

        return [item for sublist in o for item in sublist]

    @classmethod
    def find_by_email(cls, email):
        try:
            user = cls.find_one(
                Q('emails', 'eq', email)
            )
            return [user]
        except:
            return []
        # results = cls.storage.db.find({'emails':email})
        # return results

    def generate_keywords(self, save=True):
        keywords = self.fullname.lower().split(' ') #todo regex on \ +
        if self.fullname.lower() not in keywords:
            keywords.append(self.fullname.lower())
        while len(self.keywords) > 0:
            self.keywords.pop() # todo YORM
        for keyword in keywords:
            keyword_object = Keyword.load(keyword)
            if not keyword_object:
                keyword_object = Keyword()
                keyword_object._id = keyword
                keyword_object.save()
            self.keywords.append(keyword_object)
        if save:
            self.save()

User.set_storage(storage.MongoStorage(db, 'user'))