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

import sys, argparse, re
from datetime import datetime
from ldif import LDIFParser

# fritzbox
import fritzbox.phonebook


class ParseGroups(LDIFParser):
  def __init__(self, input, vipGroups, debug=False):
    self.vipGroups = vipGroups
    self.debug = debug
    LDIFParser.__init__(self, input)

  def get_value(self, entry, name):
    return unicode(entry[name][0], "utf-8") if name in entry else None

  def handle(self, dn, entry):
    #debug(entry)
    cn = self.get_value(entry, "cn")
    oc = entry["objectclass"]
    if cn and len(oc) == 2 and oc[0] == "top" and oc[1] == "groupOfNames":
      #debug(cn)      
      if cn in self.vipGroups:
        for m in entry["member"]:
          #debug(m)
          self.vipGroups[cn].append(unicode(m, "utf-8"))


class ParsePersons(LDIFParser):
  def __init__(self, input, vipGroups, debug=False):
    self.vipGroups = vipGroups
    self.debug = debug
    self.phoneBook = fritzbox.phonebook.Phonebook()
    LDIFParser.__init__(self, input)

  def handle(self, dn, entry):
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
      self.phoneBook.addContact(contact)

  def _get_value(self, entry, name):
    return unicode(entry[name][0], "utf-8") if name in entry else None

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
    with open(filename, "r") as f:
      groups = ParseGroups(f, vipGroups, debug=debug)
      groups.parse()

    # parse persons
    with open(filename, "r") as f:
      persons = ParsePersons(f, groups.vipGroups, debug=debug)
      persons.parse()
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(persons.phoneBook)
    return books

