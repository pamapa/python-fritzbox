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

import csv

# fritzbox
import fritzbox.phonebook


class FindEncodingDictReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, delimiter=',', dialect=csv.excel, encoding="utf-8"):
        self.reader = csv.DictReader(f, delimiter=delimiter, dialect=dialect)

    def __next__(self):
        row = self.reader.__next__()
        for key in row:
            if row[key] is not None:
              try:
                row[key] = row[key]
              # Special case, sometimes the content gets reqd as a list
              except AttributeError:
                  newList = []
                  for item in row[key]:
                      newList.append(item)
                  row[key] = newList
            else:
              row[key] = ''
        return row

    def __iter__(self):
        return self


def find_delimiter(filname, debug=False):
  with open(filname, 'r') as f:
    line = f.readline()
    semi_cnt = line.count(";")
    comma_cnt = line.count(",")
    delimiter = ","
    if semi_cnt >  comma_cnt: delimiter = ";"
    if debug: print("Correct delimiter is '%s'" % delimiter)
    return delimiter


def find_encoding(filname, delimiter, debug=False):
  all_encoding = [
    "utf-8", "iso-8859-1", "iso-8859-2", "iso-8859-15",
    "iso-8859-3", "us-ascii", "windows-1250", "windows-1252",
    "windows-1254", "ibm861"
  ]
  encoding_index = 0
  csv_reader = None
  while csv_reader == None:  
    next_encoding = all_encoding[encoding_index]
    if debug: print("Trying %s" % (next_encoding))
    csv_file = open(filname, "rt")
    csv_reader = FindEncodingDictReader(csv_file, delimiter=delimiter, encoding=next_encoding)
    try:
      for line in enumerate(csv_reader):
        # Do nothing, just reading the whole file
        encoding_index = encoding_index
    except UnicodeDecodeError:
      csv_reader = None
      encoding_index = encoding_index + 1

  if debug: print("Correct encoding is %s" % next_encoding)
  csv_file.close()
  return next_encoding


def getEntityPerson(fields):
  # tellows
  if "Score" in fields and "Anruftyp" in fields:
    name = "%s / score:%s" % (fields["Anruftyp"], fields["Score"])
    return fritzbox.phonebook.Person(name, "")

  givenName = ""
  for field_name in fields:
    if not field_name:
      continue
    name = field_name.lower()
    if "given name" in name or "first name" in name:
      givenName = fields[field_name]
      break
  familyName = ""
  for field_name in fields:
    if not field_name:
      continue
    name = field_name.lower()
    if "family name" in name or  "last name" in name:
      familyName = fields[field_name]
      break

  return fritzbox.phonebook.Person(givenName, familyName)


def parse_csv(filename, delimiter, encoding, debug=False):
  csv_file = open(filename, "rt")
  csv_reader = FindEncodingDictReader(csv_file, delimiter=delimiter, encoding=encoding)

  phoneBook = fritzbox.phonebook.Phonebook()
  for (line, fields) in enumerate(csv_reader):
    #if debug: print(fields)
    person = getEntityPerson(fields)
    #if debug: print(person)

    # phone number: CardDav to Fritz!Box
    map_number_names = {
      "work phone": "work",
      "home phone": "home",
      "mobile": "mobile",
      "fax": "fax"
    }
    # find numbers and categorize to "home|mobile|work|fax"
    telephony = fritzbox.phonebook.Telephony()
    for field in fields:
      if not field: continue
      number = ""
      ntype = None
      for n in map_number_names:
        if field.lower().find(n) != -1:
          number = fields[field]
          ntype = map_number_names[n]
          break
      # workaround for tellows.de: number = Land Nummer
      if field.find("Nummer") != -1 and "Land" in fields:
        number = "+%s%s" % (fields["Land"], fields[field][1:])
        ntype = "work"
      if len(number) != 0:
        telephony.addNumber(ntype, number, 0)


    # email: CardDav to Fritz!Box
    map_email_types = {
      "Primary Email":   "private",
      "Secondary Email": "private"
    }
    # find email
    services = fritzbox.phonebook.Services()
    for field in fields:
      if not field: continue
      for n in map_email_types:
        if field.lower().find(n) != -1:
          email = fields[field]
          etype = map_email_types[n]
          if len(number) != 0:
            services.addEmail(etype, email)
        break

    if telephony.hasNumbers():
      contact = fritzbox.phonebook.Contact(0, person, telephony)
      phoneBook.addContact(contact)

  csv_file.close()
  return phoneBook  


class Import(object):
  def get_books(self, filename, vipGroups, debug=False):
    delimiter = find_delimiter(filename, debug=debug)
    encoding = find_encoding(filename, delimiter, debug=debug)
    book = parse_csv(filename, delimiter, encoding, debug=debug)
    books = fritzbox.phonebook.Phonebooks()
    books.addPhonebook(book)
    return books

