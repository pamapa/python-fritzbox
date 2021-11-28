#!/usr/bin/env python3

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

import os, sys, argparse, re
from bs4 import BeautifulSoup
import urllib.request
from datetime import datetime

# fritzbox
import fritzbox.phonebook
import fritzbox.access


NAME_MAX_LENGTH = 100
g_debug = False


def extract_number(data):
  n = re.sub(r"[^0-9\+]","", data)
  return n

# 021 558 73 91/92/93/94/95
def extract_slashed_numbers(data):
  ret = []
  arr = data.split("/")
  a0 = extract_number(arr[0])
  if (a0 != ""):
    ret.append(a0)
    base = a0[0:-2]
    for ax in arr[1:]:
      ax = extract_number(ax)
      if (ax != ""):
        ax = extract_number(base + ax)
        ret.append(ax)
  return ret

# 044 400 00 00 bis 044 400 00 19
def extract_range_numbers(data):
  ret = []
  arr = re.split("bis", data)
  s = extract_number(arr[0])
  e = extract_number(arr[1])
  for i in range(int(s[-4:]), int(e[-4:])+1):
    a = s[:-4]+"%04d" % i
    ret.append(a)
  return ret

def extract_numbers(data):
  ret = []
  #print("data:" + data)
  arr = re.split("und|oder|sowie|auch|,|;", data)
  for a in arr:
    if a.find("/") != -1:
      ret.extend(extract_slashed_numbers(a))
    elif a.find("bis") != -1:
      ret.extend(extract_range_numbers(a))
    else:
      a = extract_number(a)
      if (a != ""): ret.append(a)
  return ret

def extract_name(data):
  s = data
  s = s.replace("\n", "").replace("\r", "")
  s = re.sub(r'<[^>]*>', " ", s) # remove tags
  s = s.replace("&amp", "&")
  s = s.replace("  ", " ")
  s = s.strip()
  if s.startswith("Firma: "):
    s = s[7:]
  return s if len(s)<= NAME_MAX_LENGTH else s[0:NAME_MAX_LENGTH-3]+"..."

def fetch_page(page_nr):
  if g_debug: print("fetch_page: " + str(page_nr))
  url = "https://www.ktipp.ch/service/warnlisten/detail/?warnliste_id=7&ajax=ajax-search-form&page=" + str(page_nr)
  headers = {"User-Agent": "Mozilla/5.0"}
  req = urllib.request.Request(url, headers=headers)
  data = urllib.request.urlopen(req, timeout=30)
  ret = data.read()
  ret = ret.decode("utf-8")
  return str(ret)

def extract_str(data, start_str, end_str, error_msg):
  s = data.find(start_str)
  if (s == -1): error(error_msg+". Start ("+start_str+") not found.")
  s += len(start_str)
  e = data.find(end_str, s)
  if (e == -1): error(error_msg+". End ("+end_str+") not found.")
  return data[s:e].strip()

def parse_page(soup):
  ret = []
  #if g_debug: print("parse_page...")
  list = soup.findAll("section",{"class":"teaser cf"})

  date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000")

  for e in list:
    numbers = extract_numbers(e.strong.contents[0])
    name = extract_name(str(e.p))
    for n in numbers:
      ret.append({"number":n, "name":name})
  #if g_debug: print("parse_page done")
  return ret

def parse_pages(content):
  ret = []

  soup = BeautifulSoup(content, "lxml")
  tmp = str(soup.findAll("li")[-1])
  max_page_str = extract_str(tmp, "ajaxPagerWarnlisteLoadIndex(", ")", "Can't extract max pages")
  last_page = int(max_page_str)
  if g_debug: print("Last page: %s" % last_page)
  
  ret.extend(parse_page(soup))
  #return ret
  for p in range(1,last_page+1):
    if not g_debug:
      sys.stdout.write("Fetch page %s of %s\r" % (p, last_page))
      sys.stdout.flush()
    content = fetch_page(p)
    soup = BeautifulSoup(content, "lxml")
    ret.extend(parse_page(soup))
  return ret

# remove duplicates
# remove too small numbers -> dangerous
# make sure numbers are in international format (e.g. +41AAAABBBBBB)
def cleanup_entries(arr):
  #if g_debug: print("cleanup_entries...")
  seen = set()
  uniq = []
  for r in arr:
    x = r["number"]

    # make international format
    if x.startswith("00"):  x = "+"+x[2:]
    elif x.startswith("0"): x = "+41"+x[1:]
    r["number"] = x

    # filter
    if len(x) < 4:
      # too dangerous
      if g_debug: print("Skip too small number: " + str(r))
      continue
    if not x.startswith("+"):
      # not in international format
      if g_debug: print("Skip unknown format number: " + str(r))
      continue;
    if len(x) > 16:
      # see spec E.164 for international numbers: 15 (including country code) + 1 ("+")
      if g_debug: print("Skip too long number:" + str(r))
      continue;

    # filter duplicates
    if x not in seen:
      uniq.append(r)
      seen.add(x)

  #if g_debug: print("cleanup_entries done")
  return uniq


#
# main
#
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Fetch blacklist provided by ktipp.ch")
  parser.add_argument('--debug', action='store_true')

  # action
  main = parser.add_mutually_exclusive_group(required=True)
  main.add_argument("--upload", action="store_true", default=False,
    help="upload phonebook received from Ktipp to Fritz!Box")
  main.add_argument("--save",
    help="save phonebook received from Ktipp to filename")

  # upload
  upload = parser.add_argument_group("upload")
  upload.add_argument("--hostname", default="https://fritz.box",
    help="hostname")
  upload.add_argument("--password",
    help="password")
  upload.add_argument("--phonebook-id", dest="phonebook_id", default=1,
    help="phonebook id: 0 for main phone book, 1 for next phone book in list, etc...")
  upload.add_argument("--no-cert-verify", dest="cert_verify", action="store_false", default=True,
    help="do not use certificate to verify secure connection. Default is with certificate")

  args = parser.parse_args()
  g_debug = args.debug

  if not g_debug:
    sys.stdout.write("Fetch page 0\r")
    sys.stdout.flush()
  content = fetch_page(0)
  source_date = extract_str(content, "Letzte Aktualisierung:", "<", "Can't extract creation date")
  if g_debug: print("Source date: %s" % source_date)
#  if last_update == source_date:
#    # we already have this version
#    debug("We already have this version")
#    return

  result = parse_pages(content)
  result = cleanup_entries(result)

  if len(result) == 0:
    error("nothing to proceed")
    sys.exit(0)

  mod_datetime = datetime.now()
  phoneBook = fritzbox.phonebook.Phonebook(name="ktipp")
  for r in result:
    person = fritzbox.phonebook.Person(r["name"], "")
    telephony = fritzbox.phonebook.Telephony()
    telephony.addNumber("work", r["number"])
    contact = fritzbox.phonebook.Contact(0, person, telephony, mod_datetime=mod_datetime)
    phoneBook.addContact(contact)

  books = fritzbox.phonebook.Phonebooks()
  books.addPhonebook(phoneBook)

  try:
    if args.save:
      print("save phonebook to %s..." % args.save)
      books.write(args.save)
    elif args.upload:
      print("upload phonebook to %s..." % args.hostname)
      session = fritzbox.access.Session(args.password, args.hostname, cert_verify=args.cert_verify, debug=args.debug)
      books.upload(session, args.phonebook_id)
  except Exception as ex:
    print("Error: %s" % ex)
    sys.exit(-2)

