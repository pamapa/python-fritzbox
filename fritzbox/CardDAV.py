#!/usr/bin/env python

# python-fritzbox - Automate the Fritz!Box with python
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

import requests, urlparse
import xml.etree.ElementTree as ET
import vobject

# fritzbox
import fritzbox.phonebook
import fritzbox.VCF


class Import(object):
  def _raise_for_status_code(self, resp):
    if 400 <= resp.status_code < 500 or 500 <= resp.status_code < 600:
      msg  = "Error code: " + str(resp.status_code) + "\n"
      msg += resp.content
      raise requests.exceptions.HTTPError(msg)


  def _get_xml(self, session, url_dav, settings, debug=False):
    response = session.request('PROPFIND', url_dav, headers=[], **settings)
    self._raise_for_status_code(response)
    #if debug: print("Response: %s" % response.content)
    if response.headers['DAV'].count('addressbook') == 0:
        raise Exception("URL is not a CardDAV resource")
    return response.content


  def _process_xml(self, xml, debug=False):
    namespace = "{DAV:}"
    root = ET.XML(xml)
    #if debug: print("root: %s" % ET.tostring(root, "utf-8"))
    hrefs = dict()
    for child in root:
      if child.tag != namespace + "response":
        continue
      #if len(hrefs) == 10: break
      href = ""
      etag = ""
      insert = False
      for response in child:
        if response.tag == namespace + "href":
          href = response.text
        for refprop in response:
          for props in refprop:
            if props.tag == namespace + "getcontenttype":
              if (props.text == "text/vcard" or props.text == "text/vcard; charset=utf-8" or
                  props.text == "text/x-vcard" or props.text == "text/x-vcard; charset=utf-8"):
                insert = True
            elif props.tag == namespace + "getetag":
                etag = props.text
          if insert:
            hrefs[href] = etag
    return hrefs


  def _get_vcard(self, session, url_vcard, settings, debug=False):
    if debug: print("_get_vcard(%s)" % url_vcard)
    response = session.get(url_vcard, headers=[], **settings)
    self._raise_for_status_code(response)
    #if debug: print("Response: %s" % response.content)
    card = vobject.readOne(response.content)
    return card


  def get_books(self, url, username, password, auth="basic", verify=True, vipGroups=[], debug=False):
    if debug: print("get_books(%s)" % url)

    # url base
    url_split = urlparse.urlparse(url)
    url_base = url_split.scheme + '://' + url_split.netloc

    # authentification
    settings = {"verify": verify}
    if auth == "basic":
      settings["auth"] = (username, password)
    elif auth == "digest":
      from requests.auth import HTTPDigestAuth
      settings["auth"] = HTTPDigestAuth(user, passwd)

    session = requests.session()
    xml = self._get_xml(session, url, settings, debug)
    hrefs = self._process_xml(xml, debug)
    cards = []    
    for href in hrefs.keys():
      cards.append(self._get_vcard(session, url_base + href, settings, debug))

    vcf = fritzbox.VCF.Import()
    books = vcf.get_books_by_cards(cards, vipGroups, debug=debug)
    return books

