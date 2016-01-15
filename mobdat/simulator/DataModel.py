'''
Created on Dec 26, 2015

@author: arthurvaladares
'''
import logging
from cadis.language.schema import dimension, Set, SubSet, CADIS, dimensions, sets, subsets, primarykey
from collections import namedtuple
from cadis.frame import Frame
import uuid
from mobdat.common.ValueTypes import Quaternion

logger = logging.getLogger(__name__)
LOG_HEADER = "[DATAMODEL]"

#Vector3 = namedtuple("Vector3", ['X', 'Y', 'Z'])
class Vector3(object):
    X = 0
    Y = 0
    Z = 0

    def __init__(self, X, Y, Z):
        self.X = X
        self.Y = Y
        self.Z = Z

    def __json__(self):
        return self.__dict__

    def __str__(self):
        return self.__dict__.__str__()

    def __eq__(self, other):
        if isinstance(other, Vector3):
            return (other.X == self.X and other.Y == self.Y and other.Z == self.Z)
        elif isinstance(other, tuple) or isinstance(other, list):
            return (other[0] == self.X and other[1] == self.Y and other[2] == self.Z)

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def __decode__(dic):
        return Vector3(dic['X'], dic['Y'], dic['Z'])

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
