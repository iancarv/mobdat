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

@file    PersonInfo.py
@author  Mic Bowman
@date    2013-12-03

This file defines routines used to build features of a mobdat traffic
network such as building a grid of roads. 

"""

import os, sys
import logging

# we need to import python modules from the $SUMO_HOME/tools directory
sys.path.append(os.path.join(os.environ.get("OPENSIM","/share/opensim"),"lib","python"))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib")))

import json
from mobdat.common.Location import ResidentialLocationProfile, ResidentialLocation
from mobdat.common.Person import PersonProfile, Person

logger = logging.getLogger(__name__)

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class PersonInfo :

    # -----------------------------------------------------------------
    @staticmethod
    def LoadFromFile(filename, locinfo, bizinfo) :
        with open(filename, 'r') as fp :
            perdata = json.load(fp)

        perinfo = PersonInfo()
        perinfo.Load(perdata, locinfo, bizinfo)

        return perinfo

    # -----------------------------------------------------------------
    def __init__(self) :
        self.PersonProfiles = {}
        self.PersonList = {}

        self.ResidentialLocationProfiles = {}
        self.ResidentialLocations = {}

    # -----------------------------------------------------------------
    def Load(self, perdata, locinfo, bizinfo) :
        for lpinfo in perdata['ResidentialLocationProfiles'] :
            locprofile = ResidentialLocationProfile.Load(lpinfo)
            self.ResidentialLocationProfiles[locprofile.ProfileName] = locprofile

        for linfo in perdata['ResidentialLocations'] :
            location = ResidentialLocation.Load(linfo, locinfo, self)
            self.ResidentialLocations[location.Capsule.Name] = location

        for ppinfo in perdata['PersonProfiles'] :
            profile = PersonProfile.Load(ppinfo)
            self.PersonProfiles[profile.ProfileName] = profile

        for pinfo in perdata['PersonList'] :
            person = Person.Load(pinfo, locinfo, bizinfo, self)
            self.PersonList[person.Name] = person

    # -----------------------------------------------------------------
    def Dump(self) :
        result = dict()

        result['ResidentialLocationProfiles'] = []
        for plp in self.ResidentialLocationProfiles.itervalues() :
            result['ResidentialLocationProfiles'].append(plp.Dump())

        result['ResidentialLocations'] = []
        for pl in self.ResidentialLocations.itervalues() :
            result['ResidentialLocations'].append(pl.Dump())

        result['PersonProfiles'] = []
        for profile in self.PersonProfiles.itervalues() :
            result['PersonProfiles'].append(profile.Dump())

        result['PersonList'] = []
        for person in self.PersonList.itervalues() :
            result['PersonList'].append(person.Dump())

        return result
