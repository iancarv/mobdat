#!/usr/bin/env python
"""
Copyright (c) 2014, Intel Corporation

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer. 

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution. 

* Neither the name of Intel Corporation nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 

@file    SocialConnector.py
@author  Mic Bowman
@date    2013-12-03

This module defines the SocialConnector class. This class implements
the social (people) aspects of the mobdat simulation.

"""

import os, sys
import logging
from mobdat.simulator.DataModel import Vehicle, Person, BusinessNode,\
    ResidentialNode, Road, SimulationNode
from cadis.common.IFramed import Producer, GetterSetter
from cadis.common import IFramed
import json
from uuid import UUID

sys.path.append(os.path.join(os.environ.get("SUMO_HOME"), "tools"))
sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

import heapq
import BaseConnector, EventHandler, EventTypes, Traveler

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
@Producer(Vehicle, Person, BusinessNode, Road, ResidentialNode, SimulationNode)
@GetterSetter(Vehicle, Person, BusinessNode, Road, ResidentialNode, SimulationNode)
class SocialConnector(BaseConnector.BaseConnector, IFramed.IFramed):
           
    # -----------------------------------------------------------------
    def __init__(self, settings, world, netsettings, cname, frame) :
        #EventHandler.EventHandler.__init__(self, evrouter)
        BaseConnector.BaseConnector.__init__(self, settings, world, netsettings)
        self.frame = frame
        self.__Logger = logging.getLogger(__name__)

        self.MaximumTravelers = int(settings["General"].get("MaximumTravelers", 0))
        self.TripCallbackMap = {}
        self.TripTimerEventQ = []
        self.DataFolder = settings["General"]["Data"]

        self.Travelers = {}
        self.CreateTravelers()

        self.AddBuildings()
        self.__Logger.warn('SocialConnector initialization complete')

    # -----------------------------------------------------------------
    def AddTripToEventQueue(self, trip) :
        heapq.heappush(self.TripTimerEventQ, trip)

    # -----------------------------------------------------------------
    def AddBuildings(self) :
        pass

    # -----------------------------------------------------------------
    def CreateTravelers(self) :
        #for person in self.PerInfo.PersonList.itervalues() :
        count = 0
        for name, person in self.World.IterNodes(nodetype = 'Person') :
            if count % 100 == 0 :
                self.__Logger.warn('%d travelers created', count)

            traveler = Traveler.Traveler(person, self)
            self.Travelers[name] = traveler

            count += 1
            if self.MaximumTravelers > 0 and self.MaximumTravelers < count :
                break

            
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    # EVENT GENERATORS
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    # -----------------------------------------------------------------
    def GenerateTripBegEvent(self, trip) :
        """
        GenerateTripBegEvent -- create and publish a 'tripstart' event
        at the beginning of a trip
        
        trip -- object of type Trip
        """
        pname = trip.Traveler.Person.Name
        tripid = trip.TripID
        sname = trip.Source.Name
        dname = trip.Destination.Name

        #event = EventTypes.TripBegStatsEvent(self.CurrentStep, pname, tripid, sname, dname)
        #self.PublishEvent(event)


    # -----------------------------------------------------------------
    def GenerateTripEndEvent(self, trip) :
        """
        GenerateTripEndEvent -- create and publish an event to capture
        statistics about a completed trip
        
        trip -- a Trip object for a recently completed trip
        """
        pname = trip.Traveler.Person.Name
        tripid = trip.TripID
        sname = trip.Source.Name
        dname = trip.Destination.Name

        #event = EventTypes.TripEndStatsEvent(self.CurrentStep, pname, tripid, sname, dname)
        #self.PublishEvent(event)

    # -----------------------------------------------------------------
    def GenerateAddVehicleEvent(self, trip) :
        """
        GenerateAddVehicleEvent -- generate an AddVehicle event to start
        a new trip

        trip -- Trip object initialized with traveler, vehicle and destination information
        """

        #vname = str(trip.VehicleName)
        #vtype = str(trip.VehicleType)
        #rname = str(trip.Source.Capsule.DestinationName)
        #tname = str(trip.Destination.Capsule.SourceName)
        v = Vehicle()
        v.Name = trip.VehicleName
        v.Type = trip.VehicleType
        v.Route = trip.Source.Capsule.DestinationName
        v.Target = trip.Destination.Capsule.SourceName
        self.frame.add(v)

        self.__Logger.debug('add vehicle %s of type %s from %s to %s',v.Name, v.Type, v.Route, v.Target)

        # save the trip so that when the vehicle arrives we can get the trip
        # that caused the car to be created
        self.TripCallbackMap[v.Name] = trip

        #event = EventTypes.EventAddVehicle(vname, vtype, rname, tname)
        #self.PublishEvent(event)

    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    # EVENT HANDLERS
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    # -----------------------------------------------------------------
    def HandleDeleteObjectEvent(self, event) :
        """
        HandleDeleteObjectEvent -- delete object means that a car has completed its
        trip so record the stats and add the next trip for the person

        event -- a DeleteObject event object
        """

        vname = event.ObjectIdentity
        
        trip = self.TripCallbackMap.pop(vname)
        trip.TripCompleted(self)

    # -----------------------------------------------------------------
    def update(self) :
        """
        HandleTimerEvent -- timer event happened, process pending events from
        the eventq

        event -- Timer event object
        """
        self.CurrentStep = self.frame.step

        if self.CurrentStep % 100 == 0 :
            wtime = self.WorldTime
            qlen = len(self.TripTimerEventQ)
            stime = self.TripTimerEventQ[0].ScheduledStartTime if self.TripTimerEventQ else 0.0
            self.__Logger.info('at time %0.3f, timer queue contains %s elements, next event scheduled for %0.3f', wtime, qlen, stime)


        while self.TripTimerEventQ :
            if self.TripTimerEventQ[0].ScheduledStartTime > self.WorldTime :
                break

            trip = heapq.heappop(self.TripTimerEventQ)
            trip.TripStarted(self)

    # -----------------------------------------------------------------
    def HandleShutdownEvent(self, event) :
        pass

    def __decode__(self, jsonlist, typeObj):
        objlist = []
        for data in jsonlist:
            obj = typeObj.__new__(typeObj)
            for dim in obj._dimensions:
                prop = getattr(obj, dim._name)
                if hasattr(prop, "__decode__"):
                    prop = prop.__decode__(data[dim._name])
                else:
                    prop = data[dim._name]
                setattr(obj, dim._name, prop)
            if "ID" in data:
                obj.ID = UUID(data["ID"])
            else:
                obj.ID = None
            objlist.append(obj)
        return objlist

    # -----------------------------------------------------------------
    def initialize(self, limit = None) :
        self.mybusiness = None
        # Limit the number of objects for testing purposes
        plimit = 100
        rlimit = None
        blimit = None
        if self.DataFolder:
            try:
                f = open(os.path.join(self.DataFolder,"people.js"), "r")
                jsonlist = json.loads(f.read())
                self.people = self.__decode__(jsonlist, Person)
                f.close()
                for person in self.people[:limit]:
                    self.frame.add(person)
            except:
                self.__Logger.exception("could not read data from people.js")

            try:
                f = open(os.path.join(self.DataFolder,"business.js"), "r")
                jsonlist = json.loads(f.read())
                self.business = self.__decode__(jsonlist, BusinessNode)
                f.close()
                for business in self.business[:blimit]:
                    self.frame.add(business)
            except:
                self.__Logger.exception("could not read data from business.js")

            try:
                f = open(os.path.join(self.DataFolder,"residential.js"), "r")
                jsonlist = json.loads(f.read())
                self.residential = self.__decode__(jsonlist, ResidentialNode)
                f.close()
                for residence in self.residential[:rlimit]:
                    self.frame.add(residence)
            except:
                self.__Logger.exception("could not read data from residential.js")

            try:
                f = open(os.path.join(self.DataFolder,"roads.js"), "r")
                jsonlist = json.loads(f.read())
                self.cadis_roads = self.__decode__(jsonlist, Road)
                f.close()
                for road in self.cadis_roads[:limit]:
                    self.frame.add(road)
            except:
                self.__Logger.exception("could not read data from roads.js")

            try:
                f = open(os.path.join(self.DataFolder,"intersections.js"), "r")
                jsonlist = json.loads(f.read())
                self.intersections = self.__decode__(jsonlist, SimulationNode)
                f.close()
                for intersection in self.intersections[:limit]:
                    self.frame.add(intersection)
            except:
                self.__Logger.exception("could not read data from roads.js")
        #self.SubscribeEvent(EventTypes.EventDeleteObject, self.HandleDeleteObjectEvent)
        #self.SubscribeEvent(EventTypes.TimerEvent, self.HandleTimerEvent)
        #self.SubscribeEvent(EventTypes.ShutdownEvent, self.HandleShutdownEvent)
        self.__Logger.info("Simulation started!")
        # all set... time to get to work!
        #self.HandleEvents()
