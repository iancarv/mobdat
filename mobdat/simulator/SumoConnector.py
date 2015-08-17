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

@file    SumoConnector.py
@author  Mic Bowman
@date    2013-12-03

This file defines the SumoConnector class that translates mobdat events
and operations into and out of the sumo traffic simulator.

"""
import os, sys
import logging
import subprocess
import time
sys.path.append(os.path.join(os.environ.get("SUMO_HOME"), "tools"))
sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

from sumolib import checkBinary

import traci
import traci.constants as tc
import BaseConnector, EventHandler, EventTypes
from mobdat.common import ValueTypes

import multiprocessing
import math
from multiprocessing import Manager, Process, Pool,Queue
import asyncore
import asynchat
import socket
import threading
import json

from threading import Thread
import time
import random


#from threading import Thread

#Sumo Connector is responsible to make the link between Sumo and the federate 

# This block represents the Chat function , all classes below until the ##### line has the function to make the connection to the Federate. The conection is bidirecinal.
#Since the implametation use a chat room, multiple instaces could be connected to the same socket and it would be able to communicate
#the application now just send the same information to all the applications that are connecte 
#To send information to the sumo federate Sumo connector has a Function Self.Send(element) that put in a queue the element that will be send by the Connection class 



# List of all instances that are connected 
chat_room = {}




class ChatHandler(asynchat.async_chat):
    def __init__(self, sock):
        asynchat.async_chat.__init__(self, sock=sock, map=chat_room)

        self.set_terminator('\n')
        self.buffer = []

    def collect_incoming_data(self, data):
        self.buffer.append(data)

    def found_terminator(self):
        msg = ''.join(self.buffer)
        print 'Received:', msg
        #for handler in chat_room.itervalues():
            #if hasattr(handler, 'push'):
                #handler.push(msg + '\n')
        self.buffer = []

class ChatServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self, map=chat_room)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = ChatHandler(sock)

class ChatClient(asynchat.async_chat):

     def __init__(self, host, port):
       asynchat.async_chat.__init__(self)
       self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
       self.connect((host, port))

       self.set_terminator('\n')
       self.buffer = []

     def collect_incoming_data(self, data):
        self.buffer.append(data)

     def found_terminator(self):
        msg = ''.join(self.buffer)
        print 'Received:', msg
        self.buffer = []


 


# the class connection hold the socket name and its interace 
# the connector class is the consumer of all information created by the connector, that means that it will be responsible to send the information created from the connector to the federate
#it has a queue that will store the messages untill its avalible to send it 
#it has 2 threadsm one to listen from the socket and another to send throw the socket
#a iinstance of connection has to be crated in the connector class

class Connection:
	#receive a queue created by summo connector
        def __init__(self,queue):
			
                self.q = queue
		#create the socket connection
                self.server = ChatClient('localhost', 23456)
		#create a thread to listen the socket
                self.comm =   threading.Thread(target=asyncore.loop)
                self.comm.daemon = True
                self.comm.start()
                #create a socket to send the information to the federate
		self.thread = Process(target = self.Send_Inv , args = (self.q,))
                self.thread.start()
                asyncore.loop(map=chat_room)

	#the clas is hesponsible to push and pop to the queue
        def PushQueue(self,element):
                self.q.put(element)
	def PopQueue(self):
                return self.q.get()

	#responsible to send the information throw the socket
	#receive dictionaries from the connector and tranforme it in a json object
	#adding at the and a terminator to be processed in the federate
	#send to all connected applications
        def Send_Inv(self,q):
        	while True:
           		num = q.get()
           		print "Consumed", num
           		time.sleep(1)

                        encoded_file = json.dumps(num)
                        encoded_file = encoded_file +"\r\n\r\n"
                        self.server.push(encoded_file )
                        for handler in chat_room.itervalues():
                                 if hasattr(handler, 'push'):
                                         handler.push(encoded_file)

                        
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class SumoConnector(EventHandler.EventHandler, BaseConnector.BaseConnector) :

    # -----------------------------------------------------------------
    def __init__(self, evrouter, settings, world, netsettings, cname) :
        EventHandler.EventHandler.__init__(self, evrouter)
        BaseConnector.BaseConnector.__init__(self, settings, world, netsettings)

        self.__Logger = logging.getLogger(__name__)

        # the sumo time scale is 1sec per iteration so we need to scale
        # to the 100ms target for our iteration time, this probably
        # should be computed based on the target step size
        self.TimeScale = 1.0 / self.Interval

        self.ConfigFile = settings["SumoConnector"]["ConfigFile"]
        self.Port = settings["SumoConnector"]["SumoPort"]
        self.TrafficLights = {}

        self.DumpCount = 50
        self.EdgesPerIteration = 25
	
	

        self.VelocityFudgeFactor = settings["SumoConnector"].get("VelocityFudgeFactor",0.90)

        self.AverageClockSkew = 0.0
        # self.LastStepTime = 0.0

	queue = multiprocessing.Queue()
	self.connect = Connection(queue)
        # for cf in settings["SumoConnector"].get("ExtensionFiles",[]) :
        #     execfile(cf,{"EventHandler" : self})


    # To send the information just push to the queue and the thread will send to the Federate 
    def Send(self,event):
	self.connect.PushQueue(event)
    # -----------------------------------------------------------------
    # -----------------------------------------------------------------
    def __NormalizeCoordinate(self,pos) :
        return ValueTypes.Vector3((pos[0] - self.XBase) / self.XSize, (pos[1] - self.YBase) / self.YSize, 0.0)

    # -----------------------------------------------------------------
    # see http://www.euclideanspace.com/maths/geometry/rotations/conversions/eulerToQuaternion/
    # where heading is interesting and bank and attitude are 0
    # -----------------------------------------------------------------
    def __NormalizeAngle(self,heading) :
        # convert to radians
        heading = (2.0 * heading * math.pi) / 360.0
        return ValueTypes.Quaternion.FromHeading(heading)

    # -----------------------------------------------------------------
    def __NormalizeVelocity(self, speed, heading) :
        # i'm not at all sure why the coordinates for speed are off
        # by 270 degrees... but this works
        heading = (2.0 * (heading + 270.0) * math.pi) / 360.0

        # the 0.9 multiplier just makes sure we dont overestimate
        # the velocity because of the time shifting, experience
        # is better if the car falls behind a bit rather than
        # having to be moved back because it got ahead
        x = self.VelocityFudgeFactor * self.TimeScale * speed * math.cos(heading)
        y = self.VelocityFudgeFactor * self.TimeScale * speed * math.sin(heading)

        return ValueTypes.Vector3(x / self.XSize, y / self.YSize, 0.0)

    # -----------------------------------------------------------------
    def _RecomputeRoutes(self) :
        if len(self.CurrentEdgeList) == 0 :
            self.CurrentEdgeList = list(self.EdgeList)

        count = 0
        while self.CurrentEdgeList and count < self.EdgesPerIteration :
            edge = self.CurrentEdgeList.pop()
            traci.edge.adaptTraveltime(edge, traci.edge.getTraveltime(edge))
            count += 1

    # # -----------------------------------------------------------------
    # def AddVehicle(self, vehid, routeid, typeid) :
    #     traci.vehicle.add(vehid, routeid, typeID=typeid)

    # # -----------------------------------------------------------------
    # def GetTrafficLightState(self, identity) :
    #     return traci.trafficlights.getReadYellowGreenState(identity)

    # # -----------------------------------------------------------------
    # def SetTrafficLightState(self, identity, state) :
    #     return traci.trafficlights.setRedYellowGreenState(identity, state)

    # -----------------------------------------------------------------
    
    def HandleTrafficLights(self, currentStep) :
        changelist = traci.trafficlights.getSubscriptionResults()
        for tl, info in changelist.iteritems() :
            state = info[tc.TL_RED_YELLOW_GREEN_STATE]
            if state != self.TrafficLights[tl] :
                self.TrafficLights[tl] = state
                event = EventTypes.EventTrafficLightStateChange(tl,state)
		
	        stateStr = state.__str__()
	        tlStr = tl.__str__()
		#create a dictionary with all necessary information to send to the socket
		json_dict = {'evt_type':'TrafficLightInstance','status':stateStr,'id':tlStr}
		#Send to the socket
		self.Send(json_dict)

                self.PublishEvent(event)

    # -----------------------------------------------------------------
    def HandleInductionLoops(self, currentStep) :
        changelist = traci.inductionloop.getSubscriptionResults()
        for il, info in changelist.iteritems() :
            count = info[tc.LAST_STEP_VEHICLE_NUMBER]
            if count > 0 :
                event = EventTypes.EventInductionLoop(il,count)
	        
		print il
		countStr = count.__str__()
		ilStr = il.__str__()
		#create a dictionary with all necessary information to send to the socket
		jason_dict = {'evt_type':'InductionLoop','count':countStr,'id':ilStr}	
		#self.Send(jason_dict)
		self.PublishEvent(event)

    # -----------------------------------------------------------------
    def HandleDepartedVehicles(self, currentStep) :
        dlist = traci.simulation.getDepartedIDList()
        for v in dlist :
            traci.vehicle.subscribe(v,[tc.VAR_POSITION, tc.VAR_SPEED, tc.VAR_ANGLE])

            vtype = traci.vehicle.getTypeID(v)
            pos = self.__NormalizeCoordinate(traci.vehicle.getPosition(v))
            event = EventTypes.EventCreateObject(v, vtype, pos)
	    posVet = pos.ToList()
	    vid = v.__str__().split("_")[0]
	    vid = vid[6:]
	    vid = int(vid)
	    vtype = vtype.__str__().split("l")[1][1:]
		#create a dictionary with all necessary information to send to the socket
	    json_dict = {'evt_type':'VehicleInstance','position':posVet,'id':vid,'vtype':vtype}
	    #self.Send(json_dict)
            
	    self.PublishEvent(event)

    # -----------------------------------------------------------------
    def HandleArrivedVehicles(self, currentStep) :
        alist = traci.simulation.getArrivedIDList()
        for v in alist :
            event = EventTypes.EventDeleteObject(v)
	    
	    vid = v.__str__().split("_")[0]
	    vid = vid[6:]
	    vid = int(vid)
	    #create a dictionary with all necessary information to send to the socket
	    json_dict = {'evt_type':'DeleteObject','id':vid}
	    #self.Send(json_dict)	

            self.PublishEvent(event)
    # -----------------------------------------------------------------
    def HandleVehicleUpdates(self, currentStep) :
        changelist = traci.vehicle.getSubscriptionResults()
        for v, info in changelist.iteritems() :
            pos = self.__NormalizeCoordinate(info[tc.VAR_POSITION])
            ang = self.__NormalizeAngle(info[tc.VAR_ANGLE])
            vel = self.__NormalizeVelocity(info[tc.VAR_SPEED], info[tc.VAR_ANGLE])
            event = EventTypes.EventObjectDynamics(v, pos, ang, vel)

	    posVet = pos.ToList()
	    #posVet = posVet[:3]
	    vid = v.__str__().split("_")[0]
	    vid = vid[6:]
            vid = int(vid)
	    ang_vet = ang.ToList()
	    vel_vet = vel.ToList()
	    #create a dictionary with all necessary information to send to the socket
	    json_dict = {'evt_type':"VehicleInstance",'position':posVet,'id':vid}#,'angle':ang_vet,'velocity':vel_vet}
	    self.Send(json_dict)	

            self.PublishEvent(event)
    # -----------------------------------------------------------------
    # def HandleRerouteVehicle(self, event) :
    #     traci.vehicle.rerouteTraveltime(str(event.ObjectIdentity))

    # -----------------------------------------------------------------
    def HandleAddVehicleEvent(self, event) :
        self.__Logger.debug('add vehicle %s going from %s to %s', event.ObjectIdentity, event.Route, event.Target)
        traci.vehicle.add(event.ObjectIdentity, event.Route, typeID=event.ObjectType)
        traci.vehicle.changeTarget(event.ObjectIdentity, event.Target)

    # -----------------------------------------------------------------
    # Returns True if the simulation can continue
    def HandleTimerEvent(self, event) :
        self.CurrentStep = event.CurrentStep
        self.CurrentTime = event.CurrentTime

        # Compute the clock skew
        self.AverageClockSkew = (9.0 * self.AverageClockSkew + (self.Clock() - self.CurrentTime)) / 10.0

        # handle the time scale computation based on the inter-interval
        # times
        # if self.LastStepTime > 0 :
        #     delta = ctime - self.LastStepTime
        #     if delta > 0 :
        #         self.TimeScale = (9.0 * self.TimeScale + 1.0 / delta) / 10.0
        # self.LastStepTime = ctime

        try :
            traci.simulationStep()

            self.HandleInductionLoops(self.CurrentStep)
            self.HandleTrafficLights(self.CurrentStep)
            self.HandleDepartedVehicles(self.CurrentStep)
            self.HandleVehicleUpdates(self.CurrentStep)
            self.HandleArrivedVehicles(self.CurrentStep)
        except TypeError as detail:
            self.__Logger.error("[sumoconector] simulation step failed with type error %s" % (str(detail)))
            sys.exit(-1)
        except ValueError as detail:
            self.__Logger.error("[sumoconector] simulation step failed with value error %s" % (str(detail)))
            sys.exit(-1)
        except NameError as detail:
            self.__Logger.error("[sumoconector] simulation step failed with name error %s" % (str(detail)))
            sys.exit(-1)
        except AttributeError as detail:
            self.__Logger.error("[sumoconnector] simulation step failed with attribute error %s" % (str(detail)))
            sys.exit(-1)
        except :
            self.__Logger.error("[sumoconnector] error occured in simulation step; %s" % (sys.exc_info()[0]))
            sys.exit(-1)

        self._RecomputeRoutes()

        if (event.CurrentStep % self.DumpCount) == 0 :
            count = traci.vehicle.getIDCount()
            event = EventTypes.SumoConnectorStatsEvent(self.CurrentStep, self.AverageClockSkew, count)
            self.PublishEvent(event)

        return True

    # -----------------------------------------------------------------
    def HandleShutdownEvent(self, event) :
        try :
            idlist = traci.vehicle.getIDList()
            for v in idlist :
                traci.vehicle.remove(v)

            traci.close()
            sys.stdout.flush()

            self.SumoProcess.wait()
            self.__Logger.info('shut down')
        except :
            exctype, value =  sys.exc_info()[:2]
            self.__Logger.warn('shutdown failed with exception type %s; %s' %  (exctype, str(value)))

    # -----------------------------------------------------------------
    def SimulationStart(self) :
        sumoBinary = checkBinary('sumo')
        sumoCommandLine = [sumoBinary, "-c", self.ConfigFile, "-l", "sumo.log"]

        self.SumoProcess = subprocess.Popen(sumoCommandLine, stdout=sys.stdout, stderr=sys.stderr)
        traci.init(self.Port)

        self.SimulationBoundary = traci.simulation.getNetBoundary()
        self.XBase = self.SimulationBoundary[0][0]
        self.XSize = self.SimulationBoundary[1][0] - self.XBase
        self.YBase = self.SimulationBoundary[0][1]
        self.YSize = self.SimulationBoundary[1][1] - self.YBase
        self.__Logger.warn("starting sumo connector")

        # initialize the edge list, drop all the internal edges
        self.EdgeList = []
        for edge in traci.edge.getIDList() :
            # this is just to ensure that everything is initialized first time
            traci.edge.adaptTraveltime(edge, traci.edge.getTraveltime(edge))

            # only keep the "real" edges for computation for now
            if not edge.startswith(':') :
                self.EdgeList.append(edge)
        self.CurrentEdgeList = list(self.EdgeList)

        # initialize the traffic light state
        tllist = traci.trafficlights.getIDList()
        for tl in tllist :
            self.TrafficLights[tl] = traci.trafficlights.getRedYellowGreenState(tl)
            traci.trafficlights.subscribe(tl,[tc.TL_RED_YELLOW_GREEN_STATE])

        # initialize the induction loops
        illist = traci.inductionloop.getIDList()
        for il in illist :
            traci.inductionloop.subscribe(il, [tc.LAST_STEP_VEHICLE_NUMBER])

        # subscribe to the events
        self.SubscribeEvent(EventTypes.EventAddVehicle, self.HandleAddVehicleEvent)
        self.SubscribeEvent(EventTypes.TimerEvent, self.HandleTimerEvent)
        self.SubscribeEvent(EventTypes.ShutdownEvent, self.HandleShutdownEvent)

        # all set... time to get to work!
        self.HandleEvents()
