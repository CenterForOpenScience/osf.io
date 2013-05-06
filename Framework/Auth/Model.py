from Framework.Mongo import *
from Framework.Search import Keyword

import datetime

class User(MongoObject):
    schema = {
        '_id':{},
        "username":{},
        "password":{},
        "fullname":{},
        "is_registered":{},
        "is_claimed":{},
        "verification_key":{},
        "emails":{'type':[str]},
        "email_verifications":{'type':lambda: dict()},
        "aka":{'type':[str]},
        "date_registered":{'default':lambda: datetime.datetime.utcnow()},
        "keywords":{'type':[Keyword], 'backref':['keyworded']},
    }
    _doc = {
        'name':'user',
        'version':1,
    }

    @classmethod
    def search(cls, terms):
        keywords = terms.lower().split(' ')
        if terms.lower() not in keywords:
            keywords.append(terms.lower())
        
        o = []
        for i in xrange(len(keywords)):
            o.append([])
        
        results = cls.storage.db.find({'keywords':{'$in':keywords}})
        keyword_set = set(keywords)

        for result in results:
            result_set = set(result['keywords'])
            intersection = result_set.intersection(keyword_set)
            o[len(o)-len(intersection)].append(result)

        return [item for sublist in o for item in sublist]

    @classmethod
    def find_by_email(cls, email):
        results = cls.storage.db.find({'emails':email})
        return results

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

User.setStorage(MongoCollectionStorage(db, 'user'))