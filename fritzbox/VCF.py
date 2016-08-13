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

import codecs
import vobject

# fritzbox
import fritzbox.phonebook


class Import(object):
  def get_books(self, filename, vipGroups, debug=False):
    cards = []
    with codecs.open(filename, "r", "utf-8") as infile:
      data = infile.read()
      for card in vobject.readComponents(data):
        cards.append(card)
    return self.get_books_by_cards(cards, vipGroups, debug)


  def get_books_by_cards(self, cards, vipGroups, debug=False):
    # map CardDav type to Fritz!Box type
    map_number_names = {
      "work":"work",
      "home":"home",
      "cell":"mobile",
      "fax":"fax"
    }

    book = fritzbox.phonebook.Phonebook()
    for card in cards:
      if len(card.n.value.family) == 0:
        realName = unicode(card.n.value.given, "utf-8")
      else:
        realName = unicode(card.n.value.family, "utf-8")
        if len(card.n.value.given) != 0:
          realName += ", %s" % unicode(card.n.value.given, "utf-8")
      person = fritzbox.phonebook.Person(realName)

      category = 0
      if hasattr(card, "categories"):
        for c in card.categories.value:
          if c in vipGroups:
            category = 1
            break

      # find numbers and categorize to "home|mobile|work|fax"
      telephony = fritzbox.phonebook.Telephony()
      for child in card.getChildren():
        if child.name != "TEL":
          continue
        otype = child.type_param.lower()
        if not otype in map_number_names:
          print("Error: Unknown type: '%s'" % otype)
          continue
        ntype = map_number_names[otype]
        number = child.value
        if len(number) != 0:
          telephony.addNumber(ntype, number, 0)

      if telephony.hasNumbers():
        contact = fritzbox.phonebook.Contact(category, person, telephony)
        book.addContact(contact)
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(book)
    return books

