#!/usr/bin/env python

# python-fritzbox - setup the Fritz!Box with python
# Copyright (C) 2015-2016 Patrick Ammann <pammann@gmx.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import argparse
import urllib2, urllib, cookielib
import hashlib
import xml.etree.ElementTree as ET
import ssl


class LoginException(Exception):
  pass


class Login(object):

  def __init__(self, password, hostname="https://fritz.box"):
    self.hostname = hostname
    self.password = password
    self.debug = False

  def getSessionID(self, sid = None):
    if sid == None:
      uri = "%s/login_sid.lua" % self.hostname
    else:
      uri = "%s/login_sid.lua?sid=%s" % (self.hostname, sid)

    # TODO: improve me
    # avoid invalid certificate
    ssl._create_default_https_context = ssl._create_unverified_context

    req = urllib2.urlopen(uri)
    data = req.read()
    if self.debug: print "data with sid: " + data

    doc = ET.fromstring(data)
    sid = doc.find("SID").text
    if sid != "0000000000000000": 
      return sid

    challenge = doc.find("Challenge").text
    if self.debug: print "challenge: " + challenge
    
    text = "%s-%s" % (challenge, self.password)
    text = text.encode("utf-16le")
    response = "%s-%s" % (challenge, hashlib.md5(text).hexdigest())
    post_data = urllib.urlencode({'response': response, 'page': ''})

    uri = "%s/login_sid.lua" % self.hostname
    if self.debug: print "req uri:%s data:%s" % (uri, post_data)
    req = urllib2.urlopen(uri, post_data)
    data = req.read()
    if self.debug: print "data from login: %s %s" % (req.info(), data)
    
    doc = ET.fromstring(data)
    sid = doc.find("SID").text
    if self.debug: print "found sid: %s" % sid
    
    if sid == "0000000000000000": raise LoginException("login failed")
    return sid


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Test login")
  parser.add_argument("--password", help="password", required=True)
  args = parser.parse_args()

  login = Login(args.password)
  print login.getSessionID()

