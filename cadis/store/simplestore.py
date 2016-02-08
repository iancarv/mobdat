'''
Created on Dec 14, 2015

@author: Arthur Valadares
'''

from cadis.common.IStore import IStore
from cadis.language import schema
from copy import copy, deepcopy
import httplib
import sys
import logging
import threading
from __builtin__ import type
from cadis.language.schema import StorageObjectFactory,\
    PermutationObjectfactory, permutationsets

class FrameUpdate(object):
    def __init__(self, t, store):
        self.added = set()
        self.updated = set()
        self.deleted = set()
        self.storageobj = set()
        self.objtype = t
        self.store = store

    def clear(self):
        self.added.clear()
        self.updated.clear()
        self.deleted.clear()

    def add(self, o):
        self.added.add(o._primarykey)
        if hasattr(o,"_storageobj"):
            self.storageobj.add(o._primarykey)

    def update(self, o):
        self.updated.add(o._primarykey)
        if hasattr(o,"_storageobj"):
            self.storageobj.add(o._primarykey)

    def delete(self, o):
        if o._primarykey in self.added:
            self.added.remove(o._primarkey)
        if o._primarykey in self.updated:
            self.updated.remove(o._primarkey)
        self.deleted.add(o._primarykey)

    def updatelist(self, clear=False):
        cp_added = copy(self.added)
        cp_updated = copy(self.updated)
        cp_deleted = copy(self.deleted)

        if clear:
            self.clear()

        added = []
        updated = []
        deleted = []
        for key in cp_added:
            if key not in self.store[self.objtype]:
                continue
            if key in self.storageobj:
                added.append(PermutationObjectfactory(self.store[self.objtype][key]))
            else:
                added.append(deepcopy(self.store[self.objtype][key]))
        for key in cp_updated:
            if key not in self.store[self.objtype]:
                continue
            if key in self.storageobj:
                updated.append(PermutationObjectfactory(self.store[self.objtype][key]))
            else:
                updated.append(deepcopy(self.store[self.objtype][key]))
        for key in cp_deleted:
            deleted.append(deepcopy(self.store[self.objtype][key]))

        return (added, updated, deleted)

class SimpleStore(IStore):
    '''
    classdocs
    '''
    app = None
    store = {}
    subsets = {}
    updates4sim = {}
    lock = threading.RLock()
    __Logger = logging.getLogger(__name__)

    def __init__(self):
        '''
        Constructor
        '''

        #self.store = {}
        #self.subsets = {}
        #self.updates = {}
        for t in schema.sets.union(schema.permutationsets):
            if t not in self.store:
                self.store[t] = {}
        for t in schema.subsets:
            if t not in self.subsets:
                self.subsets[t] = {}
        #for t in schema.permutedclss:
        #    self.store[t] = {}

    def register(self, sim):
        self.updates4sim[sim] = {}
        for t in schema.sets.union(schema.subsets, schema.permutationsets):
            self.updates4sim[sim][t] = FrameUpdate(t, self.store)

    def insert(self, obj, sim):
        with self.lock:
            newobjs = []
            cls = obj.__class__
            # Only accepts inserts of sets and permutations
            if cls not in self.store:
                #self.store[obj.__class__] = {}
                self.__Logger.error("ERROR! Object type supposed to exist in store")
                return False
            if obj._primarykey in self.store[cls]:
                #new = True
                self.__Logger.error("ERROR! Insert should only be used for new items")
                return False

            # if this class is a permutation of others, create permutations
            if hasattr(obj, "__dimensiontable__"):
                # newobj is the object we will keep in the Store
                # it is just a dictionary of property -> other objects in store
                obj, newobjs = self.CreatePermutationObject(obj)
                self.store[cls][obj._primarykey] = obj
            else:
                self.store[cls][obj._primarykey] = deepcopy(obj)

            # TODO: There's a better way of doing this..
            for s in self.updates4sim.keys():
                if s != sim and cls in self.updates4sim[s]:
                    try:
                        self.updates4sim[s][cls].add(obj)
                    except:
                        self.__Logger.exception("Failed to add update to update list.")

            for o in newobjs:
                for s in self.updates4sim.keys():
                    if hasattr(o, "_originalcls"):
                        self.updates4sim[s][o._originalcls].add(o)
                    else:
                        self.updates4sim[s][o.__class__].add(o)
##

    def CreatePermutationObject(self, obj):
        storageobj = StorageObjectFactory(obj)
        newobjs = set()
        for propname, cls in obj.__dimensiontable__.items():
            exist_in_store = False
            if cls not in storageobj.objectlinks:
                if obj._primarykey in self.store[cls]:
                    permutedobj = self.store[cls][obj._primarykey]
                    storageobj.objectlinks[cls] = permutedobj
                    exist_in_store = True
                else:
                    permutedobj = cls()
                    permutedobj.ID = obj.ID
                    #permutation of permutation
                    if cls in permutationsets:
                        storageobj.objectlinks[cls], nos = self.CreatePermutationObject(permutedobj)
                        newobjs.union(nos)
                    else:
                        storageobj.objectlinks[cls] = permutedobj
            else:
                permutedobj = storageobj.objectlinks[cls]

            if not exist_in_store:
                if cls != obj.__class__ and not exist_in_store:
                    # Copy the property value from user's object to store's object
                    value = getattr(obj, propname)
                    setattr(permutedobj, propname, value)
                newobjs.add(permutedobj)
                self.store[cls][permutedobj.ID] = permutedobj

        #self.store[obj.__class__][obj._primarykey] = storageobj
        #obj = storageobj
        return storageobj, newobjs

    def update(self, typeObj, primkey, sim, pushlist):
        if primkey not in self.store[typeObj]:
            self.__Logger.info("could not find key %s in store for type %s", primkey, typeObj)
            return None
        obj = self.store[typeObj][primkey]
        for pname in pushlist.keys():
            #logger.debug("Setting attributes in pushlist for ID %s: %s = %s",primkey,propname,self.pushlist[t][primkey][propname])
            if hasattr(obj, "objectlinks"):
                try:
                    #cls = typeObj.__dimensiontable__[pname]
                    pobj = self.store[obj._originalcls][primkey]
                    setattr(pobj, pname, pushlist[pname])
                except:
                    self.__Logger.exception("Something went wrong.")
            else:
                setattr(obj, pname, pushlist[pname])

        # TODO: There's a better way of doing this..
        for s in self.updates4sim.keys():
            if s != sim:
                self.updates4sim[s][typeObj].update(obj)

    def get(self, typeObj, copy = True):
        with self.lock:
            if typeObj in self.store:
                if typeObj in permutationsets:
                    res = []
                    for o in self.store[typeObj].values():
                        res.append(PermutationObjectfactory(o))
                    #self.__Logger.warn("Retrieving permuted sets not yet implemented.")
                    return res
                else:
                    if copy:
                        return deepcopy(self.store[typeObj].values())
                    else:
                        return self.store[typeObj].values()
            elif typeObj in self.subsets:
                res = deepcopy(typeObj.query(self))
                for o in res:
                    o.__class__ = typeObj
                return res
            else:
                self.__Logger.error("ERROR! Object type supposed to exist as a set or subset")
                sys.exit(0)

    def getobj(self, typeObj, key):
        if key in self.store[typeObj]:
            return copy(self.store[typeObj][key])
        else:
            self.__Logger.error("Could not find key %s for object type %s",key, typeObj)

    def updated(self, typeObj, sim):
        with self.lock:
            if typeObj in self.subsets:
                res = deepcopy(typeObj.query(self))
                for o in res:
                    o.__class__ = typeObj
                return (res, res, [])
            else:
                return self.updates4sim[sim][typeObj].updatelist(True)

    def delete(self, typeObj, obj):
        with self.lock:
            if obj._primarykey in self.store[typeObj]:
                del self.store[typeObj][obj._primarykey]

    def close(self):
        return
