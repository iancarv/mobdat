'''
Created on Dec 26, 2015

@author: arthurvaladares
'''
import logging
from cadis.language.schema import dimension, Set, SubSet, CADIS, dimensions, sets, subsets, primarykey
from collections import namedtuple
from cadis.frame import Frame
import uuid
from mobdat.common.ValueTypes import Quaternion, Vector3

logger = logging.getLogger(__name__)
LOG_HEADER = "[DATAMODEL]"

@Set
class Vehicle(CADIS):
    '''
    classdocs
    '''
    _ID = None
    @primarykey
    def ID(self):
        return self._ID

    @ID.setter
    def ID(self, value):
        self._ID = value

    _Name = None
    @dimension
    def Name(self):
        return self._Name

    @Name.setter
    def Name(self, value):
        self._Name = value

    _Type = None
    @dimension
    def Type(self):
        return self._Type

    @Type.setter
    def Type(self, value):
        self._Type = value

    _Route = None
    @dimension
    def Route(self):
        return self._Route

    @Route.setter
    def Route(self, value):
        self._Route = value

    _Target = None
    @dimension
    def Target(self):
        return self._Target

    @Target.setter
    def Target(self, value):
        self._Target = value

    _Position = Vector3(0,0,0)
    @dimension
    def Position(self):
        return self._Position

    @Position.setter
    def Position(self, value):
        self._Position = value

    _Velocity = Vector3(0,0,0)
    @dimension
    def Velocity(self):
        return self._Velocity

    @Velocity.setter
    def Velocity(self, value):
        self._Velocity = value

    _Rotation = Quaternion(0,0,0,0)
    @dimension
    def Rotation(self):
        return self._Rotation

    @Rotation.setter
    def Rotation(self, value):
        self._Rotation = value

    def __init__(self):
        self.ID = uuid.uuid4()

@SubSet(Vehicle)
class MovingVehicle(Vehicle):
    @staticmethod
    def query():
        return [c for c in Frame.Store.get(Vehicle) if c.Position != None or c.Position == (0,0,0)]  # @UndefinedVariable
