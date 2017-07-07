# python-fritzbox - Automate the Fritz!Box with python
# Copyright (C) 2015-2017 Patrick Ammann <pammann@gmx.net>
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

import sys, argparse, re
from datetime import datetime
from ldif3 import LDIFParser

# fritzbox
import fritzbox.phonebook


class ParseGroups():
  def __init__(self, vipGroupNames, debug=False):
    self._vipGroupNames = vipGroupNames
    self._debug = debug

  def get_entries(self, filename):
    parser = LDIFParser(open(filename, 'rb'))

    self._vipGroups = {}
    for g in self._vipGroupNames:
      self._vipGroups[g] = []

    for dn, entry in parser.parse():
      self._handle(dn, entry)

    return self._vipGroups

  def get_value(self, entry, name):
    return entry[name][0] if name in entry else None

  def _handle(self, dn, entry):
    #debug(entry)
    cn = self.get_value(entry, "cn")
    oc = entry["objectclass"]
    if cn and len(oc) == 2 and oc[0] == "top" and oc[1] == "groupOfNames":
      #debug(cn)      
      if cn in self._vipGroups:
        for m in entry["member"]:
          #debug(m)
          self._vipGroups[cn].append(m)


class ParsePersons():
  def __init__(self, vipGroups, debug=False):
    self.vipGroups = vipGroups
    self.debug = debug

  def get_entries(self, filename):
    parser = LDIFParser(open(filename, 'rb'))

    self._phoneBook = fritzbox.phonebook.Phonebook()
    for dn, entry in parser.parse():
      self._handle(dn, entry)
    return self._phoneBook

  def _handle(self, dn, entry):
    #debug(entry)
    cn = self._get_value(entry, "cn")

    home = self._get_value(entry, "homePhone")
    mobile = self._get_value(entry, "mobile")
    work = self._get_value(entry, "telephoneNumber")
    if home and len(home) > 0 or mobile and len(mobile) > 0 or work and len(work) > 0:
      contact = fritzbox.phonebook.Contact(
        self._get_category(entry, cn),
        self._get_person(entry, cn),
        self._get_telephony(home, mobile, work),
        service=self._get_services(entry)
      )
      self._phoneBook.addContact(contact)

  def _get_value(self, entry, name):
    return entry[name][0] if name in entry else None

  def _get_category(self, entry, cn):
      key = "cn=%s,mail=%s" % (cn, self._get_value(entry, "mail"))
      vip = 0
      for name in self.vipGroups:
        if key in self.vipGroups[name]:
          vip = 1
      return vip

  def _get_person(self, entry, cn):
      fname = self._get_value(entry, "givenName")
      sname = self._get_value(entry, "sn")
      realName = ""      
      if not sname or len(sname) == 0:
        realName = cn
      else:
        realName = sname
        if fname and len(fname) != 0:
          realName += ", %s" % fname
      return fritzbox.phonebook.Person(realName)

  def _get_telephony(self, home, mobile, work):    
    telephony = fritzbox.phonebook.Telephony()
    if home:
      telephony.addNumber("home", home, 0)
    if mobile:
      telephony.addNumber("mobile", mobile, 0)
    if work:
      telephony.addNumber("work", work, 0)
    return telephony

  def _get_services(self, entry):
    # TODO self._get_value(entry, "mail")
    return None


class Import(object):
  def get_books(self, filename, vipGroups, debug=False):
    # parse groups
    groups = ParseGroups(vipGroups, debug=debug)
    vipGroups = groups.get_entries(filename)

    # parse persons
    persons = ParsePersons(vipGroups, debug=debug)
    phoneBook = persons.get_entries(filename)
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(phoneBook)
    return books

