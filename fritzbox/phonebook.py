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

from datetime import datetime
import tempfile, urllib, urllib2

# fritzbox
import access
import multipart


class PhonebookException(Exception):
  pass


class Person(object):
  # realName: string
  # imageURL: e.g. file:///var/InternerSpeicher/FRITZ/fonpix/1.jpg
  def __init__(self, realName, imageURL=None):
    self.realName = realName
    self.imageURL = imageURL

  def __str__(self):
    ret  = "<person>"
    ret += "<realName>%s</realName>" % self.realName.encode("ISO-8859-1", "replace")
    if self.imageURL: ret += "<imageURL>%s</imageURL>" % self.imageURL
    ret += "</person>"
    return ret


class Telephony(object):
  def __init__(self):
    self.numberDict = {}

  # ntype: "home|mobile|work|fax"
  # number: string, best in international format (E.164)
  # prio: 1 for main number, else 0
  # vanity: vanity text
  # quickdial: None or 1-99
  def addNumber(self, ntype, number, prio=0, vanity=None, quickdial=None):
    if ntype != "home" and ntype != "mobile" and ntype != "work" and ntype != "fax":
      raise PhonebookException("invalid type: '%s'" % ntype)
    self.numberDict[ntype] = (number, prio, vanity, quickdial)

  def hasNumbers(self):
    return True if len(self.numberDict) != 0 else False

  def __str__(self):
    ret = "<telephony>"
    for ntype in self.numberDict:
      (number, prio, vanity, quickdial) = self.numberDict[ntype]
      ret += '<number type="%s" prio="%u"' % (ntype, prio)
      if vanity: ret += ' vanity="%s"' % vanity
      if quickdial: ret += ' quickdial="%s"' % quickdial
      ret += '>%s</number>' % number
    ret += "</telephony>"
    return ret


class Contact(object):
  # category: Very important person: 1, else 0
  # person: class Person
  # telephony: class Telephony
  # mod_datetime: datetime.datetime.now()
  def __init__(self, category, person, telephony, mod_datetime=None, service=None, setup=None):
    self.category = category
    self.person = person
    self.telephony = telephony
    self.mod_datetime  = mod_datetime

  def __str__(self):
    ret  = "<contact>\n"
    ret += "<category>%u</category>\n" % self.category
    ret += "%s\n" % str(self.person)
    ret += "%s\n" % str(self.telephony)
    ret += "<services/>" # not used yet
    ret += "<setup/>" # not used yet
    if self.mod_datetime: ret += "<mod_time>%s</mod_time>\n" % self.mod_datetime.strftime("%s")
    ret += "</contact>"
    return ret


class Phonebook(object):
  def __init__(self, owner=0, name=None):
    self.name = name
    self.contactList = []

  # contact: class Contact
  def addContact(self, contact):
    self.contactList.append(contact)

  def __str__(self):
    if self.name: ret = '<phonebook name="%s">\n' % self.name
    else: ret = '<phonebook>\n'
    for contact in self.contactList:
      ret += '%s\n' % str(contact)
    ret += '</phonebook>'
    return ret


class Phonebooks(object):
  def __init__(self):
    self.phonebookList = []

  # phonebook: class Phonebook
  def addPhonebook(self, phonebook):
    self.phonebookList.append(phonebook)

  def __str__(self):
    ret  = '<?xml version="1.0" encoding="iso-8859-1"?>\n'
    ret += "<phonebooks>\n"
    for book in self.phonebookList:
      ret += "%s\n" % str(book)
    ret += "</phonebooks>"
    return ret

  # sid: Login session ID
  # phonebookid: 0 for main phone book
  #              1 for next phone book in list, etc...
  def upload(self, session, phonebookid=0):
    tmpfile = tempfile.NamedTemporaryFile(mode="w")
    tmpfile.write(str(self))
    tmpfile.flush()

    # upload
    sid = session.get_sid()
    form = multipart.MultiPartForm()
    form.add_field("sid", sid)
    form.add_field("PhonebookId", phonebookid)
    with open(tmpfile.name, "r") as fh:
      form.add_file("PhonebookImportFile", "book.xml", fh, "text/xml")
    body = str(form)
    headers = {'Content-type': form.get_content_type(), 'Content-length': len(body)}
    resp = session.post("/cgi-bin/firmwarecfg", headers, body)
    html = resp.read()
    if html.find("Das Telefonbuch der FRITZ!Box wurde wiederhergestellt.") != 0:
      pass
    elif html.find("Beim Wiederherstellen des Telefonbuchs ist ein Fehler aufgetreten.") != 0:
      print "Error: uploading failed"
    else:
      print "Warning: unknown answer:\n%s" % html


# Only demo code, this module is used elsewhere
if __name__ == "__main__":
  mod_datetime = datetime.now()

  telephony1 = Telephony()
  telephony1.addNumber("home", "+12345678")
  contact1 = Contact(0, Person("Mr. X"), telephony1, mod_datetime)

  telephony2 = Telephony()
  telephony2.addNumber("work", "+1122334455")
  contact2 = Contact(1, Person("Mr. Y"), telephony2, mod_datetime)

  book = Phonebook()
  book.addContact(contact1)
  book.addContact(contact2)

  books = Phonebooks()
  books.addPhonebook(book)
  print str(books)

