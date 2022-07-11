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

import codecs, re
from datetime import datetime
import tempfile, urllib
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

# fritzbox
import fritzbox.multipart


class PhonebookException(Exception):
  pass


class Person(object):
  # givenName: string | None
  # familyName: string | None
  # imageURL: e.g. file:///var/InternerSpeicher/FRITZ/fonpix/1.jpg
  def __init__(self, givenName, familyName, imageURL=None):
    if givenName is None: givenName = ""
    self.givenName = givenName.strip()
    if familyName is None: familyName = ""
    self.familyName = familyName.strip()
    self.imageURL = imageURL

  def getXML(self):
    xml = ET.Element("person")
    # <given name> <family name>
    realName = "%s %s" % (self.givenName, self.familyName)
    ET.SubElement(xml, "realName").text = realName.strip()
    if self.imageURL: ET.SubElement(xml, "imageURL").text = self.imageURL
    return xml


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
      raise PhonebookException("invalid number type: '%s'" % ntype)
    self.numberDict[ntype] = (number, prio, vanity, quickdial)

  def hasNumbers(self):
    return True if len(self.numberDict) != 0 else False

  def normalizeNumbers(self, countryCode):
    for ntype in self.numberDict:
      (number, nprio, vanity, quickdial) = self.numberDict[ntype]
      number = re.sub(r"[^0-9\+ ]", "", number).strip()
      number = re.sub(r"^00", "+", number)
      number = re.sub(r"^0", countryCode, number)
      self.numberDict[ntype] = (number, nprio, vanity, quickdial)

  def calculateMainNumber(self):
    prio_list = ["home", "mobile", "work"]
    for p in prio_list:
      found = False
      for ntype in self.numberDict:
        if p == ntype:
          (number, nprio, vanity, quickdial) = self.numberDict[ntype]
          self.numberDict[ntype] = (number, 1, vanity, quickdial)
          found = True
          break
      if found: break
          
  def getXML(self):
    xml = ET.Element("telephony")
    for ntype in self.numberDict:
      (number, nprio, vanity, quickdial) = self.numberDict[ntype]
      x = ET.SubElement(xml, "number", type=ntype, prio=str(nprio))
      if vanity: x.set("vanity", vanity)
      if quickdial: x.set("quickdial", quickdial)
      x.text = number
    return xml


class Services(object):
  def __init__(self):
    self.emailDict = {}

  def addEmail(self, etype, email):
    if etype != "private":
      raise PhonebookException("invalid email type: '%s'" % etype)
    self.emailDict[etype] = email

  def getXML(self):
    xml = ET.Element("services")
    for etype in self.emailDict:
      email = self.emailDict[etype]
      x = ET.SubElement(xml, "email", classifier=etype)
      x.text = email
    return xml


class Contact(object):
  # category: Very important person: 1, else 0
  # person: class Person
  # telephony: class Telephony
  # mod_datetime: datetime.datetime.now()
  def __init__(self, category, person, telephony, services=None, setup=None, mod_datetime=None):
    if not isinstance(category, int) or not category in [0, 1]:
      raise PhonebookException("invalid category type: '%s'" % type(category))
    if not isinstance(person, Person):
      raise PhonebookException("invalid person type: '%s'" % type(person))
    if not isinstance(telephony, Telephony):
      raise PhonebookException("invalid telephony type: '%s'" % type(telephony))
    if services and not isinstance(services, Services):
      raise PhonebookException("invalid services type: '%s'" % type(services))
    if mod_datetime and not isinstance(mod_datetime, datetime):
      raise PhonebookException("invalid mod_datetime type: '%s'" % type(mod_datetime))
    self.category = category
    self.person = person
    self.telephony = telephony
    self.services = services
    self.mod_datetime  = mod_datetime

  def normalizeNumbers(self, countryCode):
    self.telephony.normalizeNumbers(countryCode)

  def calculateMainNumber(self):
    self.telephony.calculateMainNumber()

  def getXML(self):
    xml = ET.Element("contact")
    ET.SubElement(xml, "category").text = str(self.category)
    xml.append(self.person.getXML())
    xml.append(self.telephony.getXML())
    if self.services:
      xml.append(self.services.getXML())
    else:
      ET.SubElement(xml, "services")
    ET.SubElement(xml, "setup") # not used yet
    if self.mod_datetime: ET.SubElement(xml, "mod_time").text = self.mod_datetime.strftime("%s")
    return xml


class Phonebook(object):
  def __init__(self, owner=0, name=None):
    self.name = name
    self.contactList = []

  # contact: class Contact
  def addContact(self, contact):
    self.contactList.append(contact)

  def normalizeNumbers(self, countryCode):
    for contact in self.contactList:
      contact.normalizeNumbers(countryCode)

  def calculateMainNumber(self):
    for contact in self.contactList:
      contact.calculateMainNumber()

  def getXML(self):
    xml = ET.Element("phonebook")
    if self.name: xml.set("name", self.name)
    for contact in self.contactList:
      xml.append(contact.getXML())
    return xml


class Phonebooks(object):
  def __init__(self):
    self.phonebookList = []

  # phonebook: class Phonebook
  def addPhonebook(self, phonebook):
    self.phonebookList.append(phonebook)

  # phonebooks: class Phonebooks
  def addPhonebooks(self, phonebooks):
    self.phonebookList += phonebooks.phonebookList

  def normalizeNumbers(self, countryCode):
    for book in self.phonebookList:
      book.normalizeNumbers(countryCode)

  def calculateMainNumber(self):
    for book in self.phonebookList:
      book.calculateMainNumber()

  def mergeToOnePhonebook(self):
    merged = None
    for book in self.phonebookList:
      if merged is None:
        merged = book
        continue
      for contact in book.contactList:
        merged.addContact(contact)
    if merged is not None:
      self.phonebookList = [merged]

  def write(self, filename):
    xml = ET.Element("phonebooks")
    for book in self.phonebookList:
      xml.append(book.getXML())
    tree = ET.ElementTree(xml)
    if False:    
      tree.write(filename, encoding="iso-8859-1", xml_declaration=True)
    else:
      rough_string = ET.tostring(tree.getroot(), encoding="iso-8859-1", method="xml")
      reparsed = parseString(rough_string)
      pretty = reparsed.toprettyxml(indent="  ", encoding="iso-8859-1").decode("iso-8859-1")
      with open(filename, 'w', encoding="iso-8859-1") as outfile:
        outfile.write(pretty)

  # sid: Login session ID
  # phonebookid: 0 for main phone book
  #              1 for next phone book in list, etc...
  def upload(self, session, phonebookid=0):
    tmpfile = tempfile.NamedTemporaryFile(mode="w")
    self.write(tmpfile.name)
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
      print("Error: uploading failed")
    else:
      print("Warning: unknown answer:\n%s" % html)

