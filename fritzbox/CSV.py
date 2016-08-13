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

import os, sys, argparse, re
import codecs, csv
from datetime import datetime

# fritzbox
import fritzbox.phonebook


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeDictReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, delimiter=',', dialect=csv.excel, encoding="utf-8"):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.DictReader(f, delimiter=delimiter, dialect=dialect)

    def next(self):
        row = self.reader.next()
        for key in row:
            if row[key] != None:
              try:
                row[key] = row[key].decode("utf-8")
              # Special case, sometimes the content gets reqd as a list
              except AttributeError:
                  newList = []
                  for item in row[key]:
                      newList.append(item.decode("utf-8"))
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
    csv_reader = UnicodeDictReader(csv_file, delimiter=delimiter, encoding=next_encoding)
    try:
      for line in enumerate(csv_reader):
        # Do nothing, just reading the whole file
        encoding_index = encoding_index
    except UnicodeDecodeError:
      csv_reader = None
      input_csv_file.close()
      encoding_index = encoding_index + 1

  if debug: print("Correct encoding is %s" % next_encoding)
  csv_file.close()
  return next_encoding


def normalize_number(number, countryCode):
  if number:
    number = re.sub(r"[^0-9\+ ]", "", number).strip()
    number = re.sub(r"^00", "+", number)
    number = re.sub(r"^0", countryCode, number)
  return number


def getEntityPerson(fields):
  # tellows
  if "Score" in fields and "Anruftyp" in fields:
    realName = "%s / score:%s" % (fields["Anruftyp"], fields["Score"])
    return fritzbox.phonebook.Person(realName)

  first_name = ""
  for field_name in fields:
    if field_name and field_name.lower().find("first name") != -1:
      first_name = fields[field_name]
      break
  last_name = ""
  for field_name in fields:
    if field_name and field_name.lower().find("last name") != -1:
      last_name = fields[field_name]
      break

  if len(last_name) == 0:
    realName = first_name
  else:
    realName = last_name
    if len(first_name) != 0:
      realName += ", %s" % first_name
  return fritzbox.phonebook.Person(realName)


def parse_csv(filename, delimiter, encoding, debug=False):
  csv_file = open(filename, "rt")
  csv_reader = UnicodeDictReader(csv_file, delimiter=delimiter, encoding=encoding)

  date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000")
  #if debug: print(date)

  phoneBook = fritzbox.phonebook.Phonebook()
  for (line, fields) in enumerate(csv_reader):
    #if debug: print(fields)
    person = getEntityPerson(fields)
    #if debug: print(name)

    # map CSV type to Fritz!Box type
    map_number_names = {
      "work phone":"work",
      "home phone":"home",
      "mobile":"mobile",
      "fax":"fax"
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

