'''
Created on Jan 27, 2016

@author: Arthur Valadares
'''
from cadis.common.IFramed import IFramed, Producer, GetterSetter
from mobdat.simulator.DataModel import BusinessNode, SimulationNode,\
    ResidentialNode, Vehicle, Person
from prime.PrimeDataModel import PrimeNode, EmptyBusiness
import logging
from mobdat.common.ValueTypes import Vector3

@Producer(BusinessNode, SimulationNode, PrimeNode)
@GetterSetter(Vehicle, Person, BusinessNode, ResidentialNode, SimulationNode, PrimeNode, EmptyBusiness)
class PrimeSimulator(IFramed):
    def __init__(self, settings, world, netsettings, cname, frame) :
        self.frame = frame
        self.__Logger = logging.getLogger(__name__)
        pass

    def initialize(self):
        self.mybusiness = None
        self.__Logger.warn('PrimeSimulator initialization complete')

    def update(self):
        self.CurrentStep = self.frame.step
        if self.CurrentStep % 4 == 0 :
            if not self.mybusiness:
                a = self.frame.get(EmptyBusiness)
                if len(a) > 0:
                    print "Found one"
                    pn = PrimeNode()
                    print a
                    pn.ID = a[0].ID
                    pn.Name = "Amazon"
                    pn.PeakCustomerCount = 0
                    pn.Customers = ["worker1", "worker2"]
                    self.frame.add(pn)
                    self.mybusiness = pn.ID
            else:
                ppl = self.frame.get(Person)
                business = self.frame.get(PrimeNode, self.mybusiness)
                business.PeakCustomerCount += 1
                business.Center = Vector3(self.CurrentStep, 0, 0)
                business.Customers.append("worker%s" % self.CurrentStep)
