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

from ldif import LDIFParser

# fritzbox
import fritzbox.phonebook


class ParseGroups(LDIFParser):
  def __init__(self, infile, vipGroupArray, debug=False):
    LDIFParser.__init__(self, infile)
    self.vipGroupDict = {}
    for g in vipGroupArray:
      self.vipGroupDict[g] = []
    self._debug = debug

  def _handle(self, dn, entry):
    #debug(entry)
    cn = self._get_value(entry, "cn")
    oc = entry["objectclass"]
    if cn and len(oc) == 2 and oc[0] == "top" and oc[1] == "groupOfNames":
      #debug(cn)      
      if cn in self.vipGroupDict:
        for m in entry["member"]:
          #debug(m)
          self.vipGroupDict[cn].append(m)

  def _get_value(self, entry, name):
    return entry[name][0] if name in entry else None


class ParsePersons(LDIFParser):
  def __init__(self, infile, vipGroupDict, debug=False):
      LDIFParser.__init__(self, infile)
      self.phoneBook = fritzbox.phonebook.Phonebook()
      self._vipGroupDict = vipGroupDict
      self._debug = debug

  def handle(self, dn, entry):
    if self._debug:
      print("entry: %s" % entry)
    cn = self._get_value(entry, "cn")

    category = self._get_category(entry, cn)
    telephony = self._get_telephony(entry)
    services = self._get_services(entry)

    if telephony.hasNumbers():
      person = self._get_person(entry, cn)
      contact = fritzbox.phonebook.Contact(category, person, telephony, services)
      self.phoneBook.addContact(contact)

  def _get_value(self, entry, name):
    return entry[name][0].decode() if name in entry else None

  def _get_category(self, entry, cn):
      key = "cn=%s,mail=%s" % (cn, self._get_value(entry, "mail"))
      vip = 0
      for name in self._vipGroupDict:
        if key in self._vipGroupDict[name]:
          vip = 1
      return vip

  def _get_person(self, entry, cn):
      fname = self._get_value(entry, "givenName")
      sname = self._get_value(entry, "sn")

      givenName = ""
      familyName = ""
      if not sname or len(sname) == 0:
        familyName = cn
      else:
        givenName = fname
        familyName = sname

      return fritzbox.phonebook.Person(givenName, familyName)

  def _get_telephony(self, entry):
    telephony = fritzbox.phonebook.Telephony()
    # LDIF to Fritz!Box
    map_number_types = {
      "telephoneNumber": "work",
      "homePhone":       "home",
      "mobile":          "mobile"
    }
    for itype in map_number_types:
      number = self._get_value(entry, itype)
      if number and len(number) > 0:
        telephony.addNumber(map_number_types[itype], number, 0)
    return telephony

  def _get_services(self, entry):
    services = fritzbox.phonebook.Services()
    # email: LDIF to Fritz!Box
    map_email_types = {
      "mail":               "private",
      "mozillaSecondEmail": "private"
    }
    for itype in map_email_types:
      email = self._get_value(entry, itype)
      if email and len(email) > 0:
        services.addEmail(map_email_types[itype], email)
    return services


class Import(object):
  def get_books(self, filename, vipGroupArray, debug=False):
    # parse groups
    parser = ParseGroups(open(filename, "rb"), vipGroupArray, debug=debug)
    parser.parse()
    vipGroupDict = parser.vipGroupDict

    # parse persons
    parser = ParsePersons(open(filename, "rb"), vipGroupDict, debug)
    parser.parse()
    phoneBook = parser.phoneBook
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(phoneBook)
    return books
