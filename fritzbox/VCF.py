#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import os, re
import codecs
import vobject
from PIL import Image

# fritzbox
import fritzbox.phonebook


class Import(object):
  def get_books(self, filename, vipGroups, picture_path, debug=False):
    cards = []
    with codecs.open(filename, "r", "utf-8") as infile:
      data = infile.read()
      for card in vobject.readComponents(data):
        cards.append(card)
    return self.get_books_by_cards(cards, vipGroups, picture_path, debug)


  def get_books_by_cards(self, cards, vipGroups, picture_path, debug=False):
    # map CardDav type to Fritz!Box type
    map_number_names = {
      "work":   "work",
      "home":   "home",
      "home\\": "home",
      "cell":   "mobile",
      "fax":    "fax"
    }

    book = fritzbox.phonebook.Phonebook()
    for card in cards: # card: vobject.base.Component
      #print card

      # name
      if hasattr(card, "n"):
        if len(card.n.value.family) == 0:
          realName = unicode(card.n.value.given, "utf-8")
        else:
          realName = unicode(card.n.value.family, "utf-8")
          if len(card.n.value.given) != 0:
            realName += ", %s" % unicode(card.n.value.given, "utf-8")
      else:
        realName = unicode(card.fn.value, "utf-8")
      #print realName

      # category
      category = 0
      if hasattr(card, "categories"):
        for c in card.categories.value:
          if c in vipGroups:
            category = 1
            break

      # find numbers and categorize to "home|mobile|work|fax"
      telephony = fritzbox.phonebook.Telephony()
      for child in card.getChildren():
        if child.name.lower() != "tel":
          continue
        itype = child.type_param.lower()
        if not itype in map_number_names:
          print("Error: Unknown type: '%s'" % itype)
          continue
        ntype = map_number_names[itype]
        number = child.value
        if len(number) != 0:
          telephony.addNumber(ntype, number, 0)

      # picture
      imageURL = None
      if picture_path is not None and hasattr(card, "photo"):
        if card.photo.encoding_param.lower() != "b":
          print("Error: Unknown photo encoding: '%s'" % card.photo.encoding_param.lower())
          continue
        itype = card.photo.type_param.lower()
        if itype == "jpeg" or itype == "image/jpeg":
          imgtype = "jpg"
        elif itype == "png":
          imgtype = "png"
        else:
          print("Error: Unknown photo type: '%s'" % itype)
          continue

        if not os.path.exists(picture_path):
          os.makedirs(picture_path)

        # try to have nice a filename
        fname = realName.replace(u"ä", "ae").replace(u"ö", "oe").replace(u"ü", "ue")
        fname = fname.replace(u"é", "e").replace(u"è", "e").replace(u"ç", "c")
        fname = fname.replace(", ", "_")
        fname = re.sub(r"[^a-z0-9]", "_", fname, flags=re.I)
        fname = fname.lower()
        fname = "%s.jpg" % fname

        if itype == "jpg":
          with open(os.path.join(picture_path, fname), "w") as outfile:
            outfile.write(card.photo.value)
        else:
          # FRITZ!Fon: picture must be jpg
          tmp = os.path.join(picture_path, "tmp.%s" % imgtype)
          with open(tmp, "w") as outfile:
            outfile.write(card.photo.value)
          im = Image.open(tmp)
          os.remove(tmp)
          im.save(os.path.join(picture_path, fname))
        imageURL = "file:///var/InternerSpeicher/FRITZ/fonpix/%s" % fname

      if telephony.hasNumbers():
        person = fritzbox.phonebook.Person(realName, imageURL)
        contact = fritzbox.phonebook.Contact(category, person, telephony)
        book.addContact(contact)
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(book)
    return books

