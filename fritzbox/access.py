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
import urllib2, urllib, hashlib
import xml.etree.ElementTree as ET
import ssl


class SessionException(Exception):
  pass


class Session(object):

  def __init__(self, password, hostname="https://fritz.box"):
    self.password = password
    self.hostname = hostname
    self.sid = None
    self.debug = False

  def get_sid(self):
    if self.sid == None:
      uri = "%s/login_sid.lua" % self.hostname
    else:
      uri = "%s/login_sid.lua?sid=%s" % (self.hostname, self.sid)
    if self.debug: print "uri: " + uri

    # TODO: improve me
    # avoid invalid certificate
    ssl._create_default_https_context = ssl._create_unverified_context

    resp = urllib2.urlopen(uri)
    data = resp.read()
    if self.debug: print "data with sid: " + data

    doc = ET.fromstring(data)
    self.sid = doc.find("SID").text
    if self.sid != "0000000000000000": 
      return self.sid

    challenge = doc.find("Challenge").text
    if self.debug: print "challenge: " + challenge
    
    text = "%s-%s" % (challenge, self.password)
    text = text.encode("utf-16le")
    response = "%s-%s" % (challenge, hashlib.md5(text).hexdigest())
    post_data = urllib.urlencode({'response': response, 'page': ''})

    uri = "%s/login_sid.lua" % self.hostname
    if self.debug: print "req uri:%s data:%s" % (uri, post_data)
    resp = urllib2.urlopen(uri, post_data)
    data = resp.read()
    if self.debug: print "data from login: %s %s" % (resp.info(), data)
    
    doc = ET.fromstring(data)
    self.sid = doc.find("SID").text
    if self.debug: print "found sid: %s" % self.sid
    
    if self.sid == "0000000000000000": raise SessionException("login failed")
    return self.sid


  def post(self, path, headers, body):
    uri = "%s/%s" % (self.hostname, path)
    if self.debug: print "post: uri=%s, headers=%s, body=%s" % (uri, headers, body)
    request = urllib2.Request(uri)
    for header in headers:
      request.add_header(header, headers[header])
    request.add_data(body)
    resp = urllib2.urlopen(request)
    return resp

  def get(self, path, query):
    uri = "%s/%s" % (self.hostname, path)
    if self.debug: print "post: uri=%s, query=%s" % (uri, query)
    data = urllib.urlencode(query)
    request = urllib2.Request(uri, data)
    resp = urllib2.urlopen(request)
    return resp


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Test login")
  parser.add_argument("--password", help="password", required=True)
  args = parser.parse_args()

  session = Session(args.password)
  print session.get_sid()

