# python-fritzbox - Automate the Fritz!Box with python
# Copyright (C) 2015-2021 Patrick Ammann <pammann@gmx.net>
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

import os
import hashlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import ssl


CAFILE_PATH="/etc/ssl/localcerts"


class SessionException(Exception):
  pass


class Session(object):

  def __init__(self, password, url="https://fritz.box", cert_verify=True, debug=False):
    self.password = password
    self.url = urllib.parse.urlparse(url)
    self.sid = None
    self.debug = debug
    self.cafile = None
    if cert_verify:
      name = "FritzBox_%s" % self.url.hostname.replace(".", "_")
      self.cafile = "%s.crt" % os.path.join(CAFILE_PATH, name)


  def save_certificate(self):
    port = self.url.port if self.url.port else 443
    adr = (self.url.hostname, port)
    if self.debug: print("save_certificate of %s to %s" % (str(adr), self.cafile))
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
    if self.debug: print("uri: %s" % uri)

    if not self.cafile:
      # fritzbox uses self signed certificates :-(
      print("Warning: Using unverified SSL. Save the certificate of your firtzbox locally first!")
      ssl._create_default_https_context = ssl._create_unverified_context
    else:
      if self.debug: print("cafile: %s" % self.cafile)

    resp = urllib.request.urlopen(uri, cafile=self.cafile)
    data = resp.read()
    if self.debug: print("data with sid: %s" % data)

    doc = ET.fromstring(data)
    self.sid = doc.find("SID").text
    if self.sid != "0000000000000000":
      return self.sid

    challenge = doc.find("Challenge").text
    if self.debug: print("challenge: %s" % challenge)

    text = "%s-%s" % (challenge, self.password)
    text = text.encode("utf-16le")
    response = "%s-%s" % (challenge, hashlib.md5(text).hexdigest())
    post_data = urllib.parse.urlencode({'response': response, 'page': ''})

    uri = "%s/login_sid.lua" % self.url.geturl()
    if self.debug: print("req uri: %s data: %s" % (uri, post_data))
    resp = urllib.request.urlopen(uri, post_data.encode(), cafile=self.cafile)
    data = resp.read()
    if self.debug: print("data from login: %s %s" % (resp.info(), data))

    doc = ET.fromstring(data)
    self.sid = doc.find("SID").text
    if self.debug: print("found sid: %s" % self.sid)

    if self.sid == "0000000000000000": raise SessionException("login failed")
    return self.sid


  def post(self, path, headers, body):
    uri = "%s/%s" % (self.url.geturl(), path)
    if self.debug: print("post: uri=%s, headers=%s" % (uri, headers))
    request = urllib.request.Request(uri)
    for header in headers:
      request.add_header(header, headers[header])
    request.add_data(body)
    resp = urllib.request.urlopen(request, cafile=self.cafile)
    if self.debug: print("resp: %s" % resp.info())
    return resp


  def get(self, path, query):
    uri = "%s/%s" % (self.url.geturl(), path)
    if self.debug: print("get: uri=%s, query=%s" % (uri, query))
    data = urllib.urlencode(query)
    request = urllib.request.Request(uri, data)
    resp = urllib.request.urlopen(request, cafile=self.cafile)
    if self.debug: print("resp: %s" % resp.info())
    return resp
