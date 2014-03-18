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

@file    Controller.py
@author  Mic Bowman
@date    2013-12-03

This module defines routines for controling the mobdat simulator. The controller
sets up the connectors and then drives the simulation through the periodic
clock ticks.

"""

import os, sys, traceback
import logging

sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

import json

from mobdat.common import NetworkSettings, NetworkInfo, LocationInfo
from mobdat.builder import *

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def Controller(settings, pushlist) :
    """
    Controller is the main entry point for driving the network building process.

    Arguments:
    settings -- nested dictionary with variables for configuring the connectors
    """

    netsettings = NetworkSettings.NetworkSettings(settings)

    netinfo = NetBuilder.Network()
    locinfo = LocationInfo.LocationInfo()
    bizinfo = BusinessBuilder.BusinessBuilder()
    perinfo = PersonBuilder.PersonBuilder()

    bindings = {"netinfo" : netinfo, "locinfo" : locinfo, "bizinfo" : bizinfo, "perinfo" : perinfo}

    for cf in settings["Builder"].get("ExtensionFiles",[]) :
        try :
            execfile(cf, bindings)
            logger.info('loaded extension file %s', cf)
        except :
            logger.warn('unhandled error processing extension file %s\n%s', cf, traceback.format_exc(1))
            sys.exit(-1)

    for push in pushlist :
        if push == 'opensim' :
            os = OpenSimBuilder.OpenSimBuilder(settings, netinfo, netsettings)
            os.PushNetworkToOpenSim()
        elif push == 'sumo' :
            sc = SumoBuilder.SumoBuilder(settings, netinfo, netsettings)
            sc.PushNetworkToSumo()

    # write the network information back out to the netinfo file
    netinfofile = settings["General"].get("NetworkInfoFile","netinfo.js")
    logger.info('saving network data to %s',netinfofile)

    with open(netinfofile, "w") as fp :
        json.dump(netinfo.Dump(), fp, indent=2, ensure_ascii=True)

    # write the network information back out to the netinfo file
    locinfofile = settings["General"].get("LocationInfoFile","locinfo.js")
    logger.info('saving location data to %s',locinfofile)

    with open(locinfofile, "w") as fp :
        json.dump(locinfo.Dump(), fp, indent=2, ensure_ascii=True)

    # write the business information out to the file
    bizinfofile = settings["General"].get("BusinessInfoFile","bizinfo.js")
    logger.info('saving business data to %s',bizinfofile)

    with open(bizinfofile, "w") as fp :
        json.dump(bizinfo.Dump(), fp, indent=2, ensure_ascii=True)

    # write the person information out to the file
    perinfofile = settings["General"].get("PersonInfoFile","perinfo.js")
    logger.info('saving person data to %s',perinfofile)

    with open(perinfofile, "w") as fp :
        json.dump(perinfo.Dump(), fp, indent=2, ensure_ascii=True)
