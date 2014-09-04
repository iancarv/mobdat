#!/usr/bin/python
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

@file    OpenSimBuilder.py
@author  Mic Bowman
@date    2013-12-03

This file defines the opensim builder class for mobdat traffic networks.
The functions in this file will rez a mobdat network in an OpenSim region.
"""

import os, sys
import logging

# we need to import python modules from the $SUMO_HOME/tools directory
sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

from mobdat.common.graph import Edge
from mobdat.common.Utilities import AuthByUserName, GenCoordinateMap,\
    CalculateOSCoordinates, CalculateOSCoordinatesFromOrigin

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class OpenSimBuilder :

    # -----------------------------------------------------------------
    def __init__(self, settings, world, laysettings) :
        self.Logger = logging.getLogger(__name__)

        self.World = world
        self.LayoutSettings = laysettings

        self.RoadMap = {}
        self.NodeMap = {}

        try :
            AuthByUserName(settings)
            self.RegionMap = GenCoordinateMap(settings)
            woffs = settings["OpenSimConnector"]["BuildOffset"]
            self.BuildOffsetX = woffs[0]
            self.BuildOffsetY = woffs[1]

            rsize = settings["OpenSimConnector"]["RegionSize"]
            self.RegionSizeX = rsize[0]
            self.RegionSizeY = rsize[1]

            self.Scenes = settings["OpenSimConnector"]["Scenes"]

        except NameError as detail: 
            self.Logger.warn("Failed processing OpenSim configuration; name error %s", (str(detail)))
            sys.exit(-1)
        except KeyError as detail: 
            self.Logger.warn("unable to locate OpenSim configuration value for %s", (str(detail)))
            sys.exit(-1)
        except :
            exctype, value =  sys.exc_info()[:2]
            self.Logger.warn('handler failed with exception type %s; %s', exctype, str(value))
            sys.exit(-1)

    # -----------------------------------------------------------------
    def FindAssetInObject(self, assetinfo) :
        oname = assetinfo["ObjectName"]
        iname = assetinfo["ItemName"]

        for name,sim in self.Scenes.items():
            conn = sim["RemoteControl"]
            result = conn.FindObjects(pattern = oname)
            if not result["_Success"] or len(result["Objects"]) == 0 :
                continue

            objectid = result["Objects"][0]
            result = conn.GetObjectInventory(objectid)
            if not result["_Success"] :
                self.Logger.warn("Failed to get inventory from container object %s; %s",oname, result["_Message"])
                sys.exit(-1)

            for item in result["Inventory"] :
                if item["Name"] == iname :
                    return item["AssetID"]

        self.Logger.warn("Failed to locate item %s in object %s",iname, oname);
        return None

    # -----------------------------------------------------------------
    def ComputeRotation(self, sig1, sig2) :
        for i in range(4) :
            success = True
            for j in range(4) :
                if sig1[j] != sig2[(i + j) % 4] and sig2[(i + j) % 4] != '*/*' :
                    success = False
                    break

            if success :
                return i

        return -1

    # -----------------------------------------------------------------
    def ComputeLocation(self, snode, enode) :
        if snode.Name not in self.NodeMap :
            self.Logger.warn('cannot find node %s in the node map' % (snode.Name))
            return False

        if enode.Name not in self.NodeMap :
            self.Logger.warn('cannot find node %s in the node map' % (enode.Name))
            return False

        sbump = self.NodeMap[snode.Name].Padding
        ebump = self.NodeMap[enode.Name].Padding
    
        deltax = enode.X - snode.X
        deltay = enode.Y - snode.Y

        # west
        if deltax < 0 and deltay == 0 :
            s1x = snode.X - sbump
            s1y = snode.Y
            e1x = enode.X + ebump
            e1y = enode.Y

        # north
        elif deltax == 0 and deltay > 0 :
            s1x = snode.X
            s1y = snode.Y + sbump
            e1x = enode.X
            e1y = enode.Y - ebump

        # east
        elif deltax > 0 and deltay == 0 :
            s1x = snode.X + sbump
            s1y = snode.Y
            e1x = enode.X - ebump
            e1y = enode.Y

        # south
        elif deltax == 0 and deltay < 0 :
            s1x = snode.X
            s1y = snode.Y - sbump
            e1x = enode.X
            e1y = enode.Y + ebump

        else :
            self.Logger.warn('something went wrong computing the signature')
            return(0,0,0,0)

        return CalculateOSCoordinatesFromOrigin(s1x + self.BuildOffsetX, s1y + self.BuildOffsetY, e1x + self.BuildOffsetX, e1y + self.BuildOffsetY, self)

    # -----------------------------------------------------------------
    def PushNetworkToOpenSim(self) :
        self.CreateNodes()
        self.CreateRoads()

    # -----------------------------------------------------------------
    def CreateRoads(self) :

        for rname, road in self.World.IterEdges(edgetype = 'Road') :
            if rname in self.RoadMap :
                continue

            if road.RoadType.Name not in self.LayoutSettings.RoadTypeMap :
                self.Logger.warn('Failed to find asset for %s' % (road.RoadType.Name))
                continue 

            # check to see if we need to render this road at all
            if road.RoadType.Render :
                asset = self.LayoutSettings.RoadTypeMap[road.RoadType.Name][0].AssetID
                zoff = self.LayoutSettings.RoadTypeMap[road.RoadType.Name][0].ZOffset

                if type(asset) == dict :
                    asset = self.FindAssetInObject(asset)
                    self.LayoutSettings.RoadTypeMap[road.RoadType.Name][0].AssetID = asset

                (p1x, p1y),(p2x, p2y),scene = self.ComputeLocation(road.StartNode, road.EndNode)
                startparms = "{ 'spoint' : '<%f, %f, %f>', 'epoint' : '<%f, %f, %f>' }" % (p1x, p1y, zoff, p2x, p2y, zoff)

                conn = scene["RemoteControl"]
                if abs(p1x - p2x) > 0.1 or abs(p1y - p2y) > 0.1 :
                    result = conn.CreateObject(asset, pos=[p1x, p1y, zoff], name=road.Name, parm=startparms)

            # build the map so that we do render the reverse roads
            self.RoadMap[Edge.GenEdgeName(road.StartNode, road.EndNode)] = True
            self.RoadMap[Edge.GenEdgeName(road.EndNode, road.StartNode)] = True
    

    # -----------------------------------------------------------------
    def CreateNode(self, name, node) :
        tname = node.IntersectionType.Name
        sig1 = node.Signature()

        if tname not in self.LayoutSettings.IntersectionTypeMap :
            self.Logger.warn('Unable to locate node type %s' % (tname))
            return

        success = False
        for itype in self.LayoutSettings.IntersectionTypeMap[tname] :
            sig2 = itype.Signature

            rot = self.ComputeRotation(sig1, sig2)
            if rot >= 0 :
                self.NodeMap[name] = itype

                (p1x,p1y),sim = CalculateOSCoordinates(node.X + self.BuildOffsetX, node.Y + self.BuildOffsetY, self)

                p1z = itype.ZOffset
                asset = itype.AssetID
                if type(asset) == dict :
                    asset = self.FindAssetInObject(asset)
                    itype.AssetID = asset

                startparms = "{ 'center' : '<%f, %f, %f>', 'angle' : %f }" % (p1x, p1y, p1z, 90.0 * rot)

                if node.IntersectionType.Render :
                    result = sim["RemoteControl"].CreateObject(asset, pos=[p1x, p1y, p1z], name=name, parm=startparms)

                success = True
                break

        if not success :
            self.NodeMap[name] = self.LayoutSettings.IntersectionTypeMap[tname][0]
            self.Logger.warn("No match for node %s with type %s and signature %s" % (name, tname, sig1))

    # -----------------------------------------------------------------
    def CreateNodes(self) :

        for name, node in self.World.IterNodes(nodetype = 'Intersection') :
            self.CreateNode(name, node)

        for name, node in self.World.IterNodes(nodetype = 'EndPoint') :
            self.CreateNode(name, node)
