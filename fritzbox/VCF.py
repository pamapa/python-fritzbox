# -*- coding: utf-8 -*-

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
import re
import codecs
import vobject
import logging

from PIL import Image
from PIL import ImageOps

# fritzbox
import fritzbox.phonebook


class Import(object):
  def get_books(self, filename, vipGroups, picture_path, logger: logging.Logger=logging.getLogger()):
    cards = []
    with codecs.open(filename, "r", "utf-8") as infile:
      data = infile.read()
      for card in vobject.readComponents(data):
        cards.append(card)
    return self.get_books_by_cards(cards, vipGroups, picture_path, logger)


  def get_books_by_cards(self, cards, vipGroups, picture_path, logger: logging.Logger):
    # phone number: CardDav to Fritz!Box
    map_number_types = {
      "work":   "work",
      "home":   "home",
      "home\\": "home",
      "cell":   "mobile",
      "fax":    "fax",
      "voice":  "home"
    }
    # email: CardDav to Fritz!Box
    map_email_types = {
      "home":   "private"
    }
    # photo
    map_image_types = {
      "jpeg":       "jpg",
      "image/jpeg": "jpg",
      "png":        "png"
    }

    book = fritzbox.phonebook.Phonebook()
    for card in cards: # card: vobject.base.Component
      #logger.debug(card)

      # name
      givenName = ""
      familyName = ""
      if hasattr(card, "n"):
        givenName = card.n.value.given
        familyName = card.n.value.family
      else:
        tmp = card.fn.value
        tmp_split = tmp.split(" ")
        if len(tmp_split) == 2:
          givenName = tmp_split[0]
          familyName = tmp_split[1]
        else:
          givenName = tmp
        logger.warn("N field missing, using FN field instead: '%s'" % givenName)
      #logger.debug("Name: %s %s" % (givenName, familyName))

      # category
      category = 0
      if hasattr(card, "categories"):
        for c in card.categories.value:
          if c in vipGroups:
            category = 1
            break

      # find phone number and categorize to "home|mobile|work|fax"
      telephony = fritzbox.phonebook.Telephony()
      for child in card.getChildren():
        if child.name.lower() != "tel":
          continue

        params_types = child.params.get("TYPE", [])
        itype = self._get_params_type(params_types, map_number_types)
        if itype is None:
          logger.warn("Phone number missing/unsupported TYPE, using 'home' instead (%s %s, %s)" % (givenName, familyName, params_types))
          itype = "home"

        ntype = map_number_types[itype]
        number = child.value
        if len(number) != 0:
          telephony.addNumber(ntype, number, 0)

      # find email
      services = fritzbox.phonebook.Services()
      for child in card.getChildren():
        if child.name.lower() != "email":
          continue

        params_types = child.params.get("TYPE", [])
        itype = self._get_params_type(params_types, map_email_types)
        if itype is None:
          logger.warn("Email missing/unsupported TYPE, using 'home' instead (%s %s, %s)" % (givenName, familyName, params_types))
          itype = "home"

        etype = map_email_types[itype]
        email = child.value
        if len(email) != 0:
          services.addEmail(etype, email)

      # picture
      imageURL = None
      if picture_path is not None and hasattr(card, "photo"):
        params_types = card.photo.params.get("TYPE", [])
        itype = self._get_params_type(params_types, map_image_types)
        if itype is None:
          logger.error("Not supported photo type (%s %s): '%s'" % (givenName, familyName, params_types))
          continue
        if card.photo.encoding_param.lower() != "b":
          logger.error("Unknown photo encoding (%s %s): '%s'" % (givenName, familyName, card.photo.encoding_param.lower()))
          continue

        if not os.path.exists(picture_path):
          os.makedirs(picture_path)

        # try to have a nice filename (format must be jpg)
        fname = "%s %s" % (givenName, familyName)
        fname = fname.replace(u"ä", "ae").replace(u"ö", "oe").replace(u"ü", "ue")
        fname = fname.replace(u"é", "e").replace(u"è", "e").replace(u"ç", "c")
        fname = re.sub(r"[^a-z0-9]", " ", fname, flags=re.I)
        fname = " ".join(fname.split())
        fname = fname.replace(" ", "_")
        fname = fname.lower()
        fname = "%s.jpg" % fname

        # copy into Image object
        imgtype = map_image_types[itype]
        tmp = os.path.join(picture_path, "tmp.%s" % imgtype)
        with open(tmp, "wb") as outfile:
          outfile.write(card.photo.value)
        img = Image.open(tmp)
        os.remove(tmp)

        # make image fit on Fritz!Fon
        max_size = (128, 128)
        width, height = img.size
        if width != height:
          logger.warn("Photo not square (%s %s %s): make it square with %s" % (givenName, familyName, img.size, max_size))
          img = ImageOps.fit(img, max_size, Image.BICUBIC)
        elif img.size > max_size:
          logger.warn("Photo too big (%s %s %s): resize to %s" % (givenName, familyName, img.size, max_size))
          img = img.resize(max_size, Image.BICUBIC)

        # remove alpha channel if there
        img = img.convert("RGB")

        # save          
        img.save(os.path.join(picture_path, fname))
        imageURL = "file:///var/InternerSpeicher/FRITZ/fonpix/%s" % fname

      if telephony.hasNumbers():
        person = fritzbox.phonebook.Person(givenName, familyName, imageURL)
        contact = fritzbox.phonebook.Contact(category, person, telephony, services)
        book.addContact(contact)
    
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(book)
    return books

  def _get_params_type(self, params_types, map_types):
    for a in params_types:
      for key in map_types:
        if a.lower() == key:
          return key
    return None
