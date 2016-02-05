'''
Created on Jan 27, 2016

@author: Arthur Valadares
'''
from cadis.language.schema import PermutedSet, Permutation, dimension, SubSet
from mobdat.simulator.DataModel import BusinessNode, SimulationNode, Person
from copy import copy

@PermutedSet
class PrimeNode(Permutation):
    ### Properties from BusinessNode
    __import_dimensions__ = [
                                SimulationNode.Center,
                                SimulationNode.Angle,
                                SimulationNode.Name,
                                SimulationNode.Rezcap,
                                BusinessNode.CustomersPerNode,
                                BusinessNode.PeakCustomerCount,
                            ]
    ### New properties

    _Customers = []
    @dimension
    def Customers(self):
        return self._Customers

    @Customers.setter
    def Customers(self, value):
        self._Customers = value

@SubSet(BusinessNode)
class EmptyBusiness(BusinessNode):
    cache = set()
    @staticmethod
    def query(store):
        bns = store.get(BusinessNode, False)
        res = []
        ppl = store.get(Person, False)
        for b in bns:
            occupied = False
            for p in ppl:
                if p.EmployedBy == b.Name:
                    occupied = True
                    continue
            if not occupied:
                res.append(b)
        return res