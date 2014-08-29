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

@file    Utilities.py
@author  Mic Bowman
@date    2014-02-04

This file defines routines used to build profiles for people and places.

"""

import os, sys
import logging
import time
import OpenSimRemoteControl
import getpass
import uuid

# we need to import python modules from the $SUMO_HOME/tools directory
sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
_NameCounts = {}

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def AuthByUserName(settings) :
    for sname,sim in settings["OpenSimConnector"]["Scenes"].items():
        endpoint = sim["EndPoint"] if "EndPoint" in sim else \
            exit('No endpoint defined for Scene {0}'.format(sname))
        avname = sim["AvatarName"] if "AvatarName" in sim else \
            exit('No avatar name specified to login in Scene {0}'.format(sname))
        domains = sim["Domain"] if "Domain" in sim else ['Dispatcher', 'RemoteControl']
        lifespan = sim["LifeSpan"] if "LifeSpan" in sim else 3600
        passwd = sim["Password"] if "Password" in sim else None

        if not passwd :
            print "Please type the password for User {0} in Scene {1}".format(avname,sname)
            passwd = getpass.getpass()

        rc = OpenSimRemoteControl.OpenSimRemoteControl(endpoint)
        rc.DomainList = domains
        response = rc.AuthenticateAvatarByName(avname,passwd,lifespan)
        if not response['_Success'] :
            print 'Failed: ' + response['_Message']
            sys.exit(-1)

        expires = response['LifeSpan'] + int(time.time())
        print >> sys.stderr, 'capability granted, expires at %s' % time.asctime(time.localtime(expires))

        print "Capability of %s is %s" % (sname,response['Capability'])
        sim["Capability"] = response['Capability'].encode('ascii')
        sim["LifeSpan"] = response['LifeSpan']

        rc_info = rc.Info()
        sim["EndPoint"] = rc_info['SynchEndPoint'].encode('ascii')
        sim["AsyncEndPoint"] = rc_info['AsyncEndPoint'].encode('ascii')

        sim["Connector"] = rc
        rc.Capability = uuid.UUID(sim["Capability"])
        rc.Scene = sname

    return True

def GenCoordinateMap(settings):
    map = settings["OpenSimConnector"]["Map"] = {}
    for _,sim in settings["OpenSimConnector"]["Scenes"].items():
        map[str(sim["Location"])] = sim["Connector"]
    return map


def GenName(prefix) :
    global _NameCounts
    
    if prefix not in _NameCounts :
        _NameCounts[prefix] = 0
    _NameCounts[prefix] += 1

    return prefix + str(_NameCounts[prefix])

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
def GenNameFromCoordinates(x, y, prefix = 'node') :
    ewdir = 'W' if x < 0 else 'E'
    nsdir = 'S' if y < 0 else 'N'
    return "%s%d%s%d%s" % (prefix, abs(x), ewdir, abs(y), nsdir)

def CalculateOSCoordinates(x, y, builder):
    locx = int(x / builder.RegionSizeX)
    locy = int(y / builder.RegionSizeY)
    coord = [locx,locy]

    scene = builder.RegionMap[str(coord)]

    convX = x % builder.RegionSizeX
    convY = y % builder.RegionSizeY

    return (convX,convY),scene

def CalculateOSCoordinatesFromOrigin(ox, oy, x, y, builder):
    (conv_ox,conv_oy),conn = CalculateOSCoordinates(ox, oy, builder)

    # Calculate region cartesian coordinates
    rx = int(ox / builder.RegionSizeX)
    ry = int(oy / builder.RegionSizeX)

    # Subtract region cartestian coordinates of origin * region size to obtain new destination coordinate
    x -= rx * builder.RegionSizeX
    y -= ry * builder.RegionSizeY

    return (conv_ox,conv_oy),(x,y),conn

