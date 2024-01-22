#!/usr/bin/env python3

# python-fritzbox - Automate the Fritz!Box with python
# Copyright (C) 2015-2024 Patrick Ammann <pammann@gmx.net>
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

import sys
import argparse
import re
from bs4 import BeautifulSoup
import urllib.request
from datetime import datetime
import traceback
import logging

# fritzbox
sys.path.append("..")
import fritzbox.phonebook
import fritzbox.access


NAME_MAX_LENGTH = 100


class FritzboxKTippCH(object):
    def __init__(self) -> None:
        self.logger = logging.getLogger("fritzboxktipp")

    def _extract_number(self, data):
        n = re.sub(r"[^0-9\+]","", data)
        return n

    def _extract_name(self, data):
        s = data
        s = s.replace("\n", "").replace("\r", "")
        s = re.sub(r'<[^>]*>', " ", s) # remove tags
        s = s.replace("&amp", "&")
        s = s.replace("  ", " ")
        s = s.strip()
        if s.startswith("Firma: "): s = s[7:]
        #self.logger.debug("_extract_name() data:'%s' -> '%s'" % (data, s))
        return s if len(s)<= NAME_MAX_LENGTH else s[0:NAME_MAX_LENGTH-3]+"..."

    def _http_get(self, url):
        self.logger.debug("http_get: '%s'" % url)
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=60)
        ret = data.read()
        ret = ret.decode("utf-8", "ignore")
        return str(ret)

    def _fetch_page(self, page_nr):
        #self.logger.debug("_fetch_page: " + str(page_nr))
        url = "https://www.ktipp.ch/service/warnlisten/detail/warnliste/unerwuenschte-oder-laestige-telefonanrufe/"
        url += "?tx_updkonsuminfo_konsuminfofe[%40widget_0][currentPage]=" + str(page_nr)
        ret = self._http_get(url)
        #self.logger.debug("%s\n%s\n%s" % ("-"*80, ret, "-"*80))
        return ret

    def _parse_page(self, soup):
        ret = []
        #self.logger.debug("parse_page...")
        content = soup.find("div", id="warnlisteContent")
        number_list = content.findAll("article")
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000")
        for e in number_list:
            number = self._extract_number(e.find("h3").get_text())
            e.h3.decompose()  # remove h3
            name = self._extract_name(str(e))
            self.logger.debug("number:'%s' name:'%s'" % (number, name))
            ret.append({"number": number, "name": name, "date_created": now, "date_modified": now})
        #self.logger.debug("parse_page done")
        return ret

    def _parse_pages(self):
        ret = []

        content = self._fetch_page(1)
        soup = BeautifulSoup(content, "lxml")
        ret.extend(self._parse_page(soup))

        # already parsed?
        current_update = ret[0]["number"]  # newest added number
        self.logger.debug("Current update: '%s'" % current_update)

        # find last page
        tmp = soup.find("div", id="warnlisteContent")
        tmp = tmp.findAll("li")[-2]
        a = tmp.find("a", href=True)
        last_page = int(a.string)
        self.logger.debug("last_page: %d" % last_page)

        # TEST
        #last_page = 2

        for p in range(2, last_page + 1):
            content = self._fetch_page(p)
            soup = BeautifulSoup(content, "lxml")
            ret.extend(self._parse_page(soup))
            #self.logger.debug("entries: %d" % len(ret))
        return ret

    def get_result(self):
        entries = self._parse_pages()
        entries = self._cleanup_entries(entries, country_code="+41")
        return entries

    # remove duplicates
    # remove too small numbers -> dangerous
    # make sure numbers are in international format (e.g. +41AAAABBBBBB)
    def _cleanup_entries(self, arr, country_code="+41"):
        self.logger.debug("cleanup_entries (num=%s)" % len(arr))
        seen = set()
        uniq = []
        for r in arr:
            x = r["number"]

            # make international format
            if x.startswith("00"):  x = "+" + x[2:]
            elif x.startswith("0"): x = country_code + x[1:]
            else: x = country_code + x
            r["number"] = x

            # filter
            if len(x) < 5:
                # too dangerous
                self.logger.debug("Skip too short number: " + str(r))
                continue
            if not x.startswith("+"):
                # not in international format
                self.logger.debug("Skip unknown format number: " + str(r))
                continue
            if len(x) > 16:
                # see spec E.164 for international numbers: 15 (including country code) + 1 ("+")
                self.logger.debug("Skip too long number:" + str(r))
                continue

            # filter duplicates
            if x not in seen:
                uniq.append(r)
                seen.add(x)
            else:
                self.logger.debug("Skip duplicate number:" + str(r))
        self.logger.debug("cleanup_entries done (num=%s)" % len(uniq))
        return uniq


#
# main
#
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch blacklist provided by ktipp.ch")
    parser.add_argument('--debug', action='store_true')
    # action
    main = parser.add_mutually_exclusive_group(required=True)
    main.add_argument("--save",
        help="save phonebook received from Ktipp to filename")
    if False:
        main.add_argument("--upload", action="store_true", default=False,
            help="upload phonebook received from Ktipp to Fritz!Box")

    if False:
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

    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h2 = logging.StreamHandler()
    h2.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO, handlers=[h1, h2])
    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    ktipp = FritzboxKTippCH()
    result = ktipp.get_result()
    if len(result) == 0:
        print("nothing to proceed")
        sys.exit(0)

    mod_datetime = datetime.now()
    phoneBook = phonebook.Phonebook(name="ktipp")
    for r in result:
        person = phonebook.Person(r["name"], "")
        telephony = phonebook.Telephony()
        telephony.addNumber("work", r["number"])
        contact = phonebook.Contact(0, person, telephony, mod_datetime=mod_datetime)
        phoneBook.addContact(contact)

    books = phonebook.Phonebooks()
    books.addPhonebook(phoneBook)

    try:
        if args.save:
            print("save phonebook to %s..." % args.save)
            books.write(args.save)
        elif False and args.upload:
            print("upload phonebook to %s..." % args.hostname)
            session = fritzbox.access.Session(args.password, args.hostname, cert_verify=args.cert_verify, logger=logger)
            books.upload(session, args.phonebook_id)
    except Exception as ex:
        logging.error(ex)
        logging.debug(traceback.format_exc())
        sys.exit(-2)
