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

import os, argparse
import urlparse, urllib2, urllib, hashlib
import xml.etree.ElementTree as ET
import ssl


CAFILE_PATH="/etc/ssl/localcerts"


class SessionException(Exception):
  pass


class Session(object):

  def __init__(self, password, url="https://fritz.box", usecafile=True, debug=False):
    self.password = password
    self.url = urlparse.urlparse(url)
    self.sid = None
    self.debug = debug
    self.cafile = None
    if usecafile:
      name = "FritzBox_%s" % self.url.hostname.replace(".", "_")
      self.cafile = "%s.crt" % os.path.join(CAFILE_PATH, name)


  def save_certificate(self):
    port = self.url.port if self.url.port else 443
    adr = (self.url.hostname, port)
    if self.debug: print "save_certificate of %s to %s" % (str(adr), self.cafile)
    capath = os.path.dirname(self.cafile)
    if not os.path.exists(capath): os.makedirs(capath)
    cert = ssl.get_server_certificate(adr)
    with open(self.cafile, "w") as outfile:
      outfile.write(cert)


  def get_sid(self):
    if self.sid == None:
      uri = "%s/login_sid.lua" % self.url.geturl()
    else:
      uri = "%s/login_sid.lua?sid=%s" % (self.url.geturl(), self.sid)
    if self.debug: print "uri: " + uri

    if not self.cafile:
      # fritzbox uses self signed certificates :-(
      print("Warning: Using unverified SSL. Save the certificate of your firtzbox locally first!")
      ssl._create_default_https_context = ssl._create_unverified_context
    else:
      if self.debug: print "cafile: " + self.cafile

    resp = urllib2.urlopen(uri, cafile=self.cafile)
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

    uri = "%s/login_sid.lua" % self.url.geturl()
    if self.debug: print "req uri:%s data:%s" % (uri, post_data)
    resp = urllib2.urlopen(uri, post_data, cafile=self.cafile)
    data = resp.read()
    if self.debug: print "data from login: %s %s" % (resp.info(), data)

    doc = ET.fromstring(data)
    self.sid = doc.find("SID").text
    if self.debug: print "found sid: %s" % self.sid

    if self.sid == "0000000000000000": raise SessionException("login failed")
    return self.sid


  def post(self, path, headers, body):
    uri = "%s/%s" % (self.url.geturl(), path)
    if self.debug: print "post: uri=%s, headers=%s" % (uri, headers)
    request = urllib2.Request(uri)
    for header in headers:
      request.add_header(header, headers[header])
    request.add_data(body)
    resp = urllib2.urlopen(request, cafile=self.cafile)
    if self.debug: print "resp: %s" % resp.info()
    return resp


  def get(self, path, query):
    uri = "%s/%s" % (self.url.geturl(), path)
    if self.debug: print "get: uri=%s, query=%s" % (uri, query)
    data = urllib.urlencode(query)
    request = urllib2.Request(uri, data)
    resp = urllib2.urlopen(request, cafile=self.cafile)
    if self.debug: print "resp: %s" % resp.info()
    return resp


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Test login")
  parser.add_argument("--password", help="password", required=True)
  args = parser.parse_args()

  session = Session(args.password, debug=True)
  #session.save_certificate()
  print session.get_sid()

