'''
Created on Dec 14, 2015

@author: Arthur Valadares
'''

from cadis.common.IStore import IStore;
from cadis.language import schema
from copy import deepcopy
import httplib
import sys

class SimpleStore(IStore):
    '''
    classdocs
    '''
    app = None
    store = {}
    subsets = {}

    def __init__(self):
        '''
        Constructor
        '''
        self.store = {}
        self.subsets = {}
        for t in schema.sets:
            self.store[t] = {}
        for t in schema.subsets:
            self.subsets[t] = {}

    def insert(self, obj):
        # Only accepts inserts of sets
        if obj.__class__ not in self.store:
            #self.store[obj.__class__] = {}
            print "ERROR! Object type supposed to exist in store"
            sys.exit(0)
        self.store[obj.__class__][obj._primarykey] = obj

    def get(self, typeObj):
        if typeObj in self.store:
            return deepcopy(self.store[typeObj].values())
        elif typeObj in self.subsets:
            res = deepcopy(typeObj.query())
            for o in res:
                o.__class__ = typeObj
            return res
        else:
            print "ERROR! Object type supposed to exist as a set or subset"
            sys.exit(0)

    def delete(self, typeObj, obj):
        #conn = httplib.HTTPConnection('www.foo.com')
        #conn.request('PUT', '/myurl', body)
        #resp = conn.getresponse()
        #content = resp.read()
        if obj._primarykey in self.store[typeObj]:
            del self.store[typeObj][obj._primarykey]

    def close(self):
        return
