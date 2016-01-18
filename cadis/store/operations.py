'''
Created on Jan 13, 2016

@author: Ian Carvalho
'''

class StoreOperation(object):
	'''
    classdocs
    '''
    def __init__(self):
        '''
        Constructor
        '''

    def apply(self):
    	pass

class UpdateOperation(StoreOperation):
	'''
    classdocs
    '''
    def __init__(self, store, obj, timestamp=None):
        self.store = store
        self.obj = obj
        self.timestamp = timestamp

    def apply():

