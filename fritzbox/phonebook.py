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

import datetime
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
  
  def _write(self, outfile):
    outfile.write("<person>")
    outfile.write("<realName>%s</realName>" % self.realName.encode("ISO-8859-1"))
    if self.imageURL: outfile.write("<imageURL>%s</imageURL>" % self.imageURL)
    outfile.write("</person>\n")


class Telephony(object):
  def __init__(self):
    self.numberDict = {}

  # type: "home|mobile|work"
  # number: string, best in international format (E.164)
  # prio: 1 for main number, else 0
  # vanity: vanity text
  # quickdial: None or 1-99
  def addNumber(self, type, number, prio=0, vanity=None, quickdial=None):
    if type != "home" and type != "mobile" and type != "work":
      raise PhonebookException("invalid type: %s" % type)
    self.numberDict[type] = (number, prio, vanity, quickdial)

  def _write(self, outfile):
    outfile.write("<telephony>")
    for type in self.numberDict:
      (number, prio, vanity, quickdial) = self.numberDict[type]
      outfile.write('<number type="%s" prio="%u"' % (type, prio))
      if vanity: outfile.write(' vanity="%s"' % vanity)
      if quickdial: outfile.write(' quickdial="%s"' % quickdial)
      outfile.write('>%s</number>' % number)
    outfile.write("</telephony>\n")


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

  def _write(self, outfile):
    outfile.write("<contact>\n")
    outfile.write("<category>%u</category>\n" % self.category)
    self.person._write(outfile)
    self.telephony._write(outfile)
    outfile.write("<services/>") # not used yet
    outfile.write("<setup/>") # not used yet
    if self.mod_datetime: outfile.write("<mod_time>%s</mod_time>\n" % self.mod_datetime.strftime("%s"))
    outfile.write("</contact>\n")


class Phonebook(object):
  def __init__(self):
    self.contactList = []

  # contact: class Contact
  def addContact(self, contact):
    self.contactList.append(contact)
    
  def _write(self, outfile):
    outfile.write("<phonebook>\n")
    for contact in self.contactList:
      contact._write(outfile)
    outfile.write("</phonebook>\n")


class Phonebooks(object):
  def __init__(self):   
    self.phonebookList = []

  # phonebook: class Phonebook
  def addPhonebook(self, phonebook):
    self.phonebookList.append(phonebook)

  # outfile: file handle
  def save(self, outfile):
    outfile.write('<?xml version="1.0" encoding="iso-8859-1"?>\n')
    outfile.write("<phonebooks>\n")
    for book in self.phonebookList:
      book._write(outfile)
    outfile.write("</phonebooks>\n")
      
  # sid: Login session ID
  # phonebookid: phonebook id, 0 for main phone book
  def upload(self, session, phonebookid=0):
    tmpfile = tempfile.NamedTemporaryFile(mode="w")
    self.save(tmpfile)
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
    data = resp.read()
    #print data


# Only demo code, this module is by others
if __name__ == "__main__":
  mod_datetime = datetime.datetime.now()

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
  with open("test.xml", "w") as outfile:
    books.save(outfile)

