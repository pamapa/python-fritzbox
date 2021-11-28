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

import os
import sys
import argparse

# fritzbox modules
import fritzbox.phonebook
import fritzbox.access
import fritzbox.CSV
import fritzbox.LDIF
import fritzbox.VCF
import fritzbox.CardDAV


#
# main
#
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Fritz!Box util")
  parser.add_argument('--debug', action='store_true')

  # action
  main = parser.add_mutually_exclusive_group(required=True)
  main.add_argument("--save",
    help="save phonebook specified with LOAD to local file")
  if False:
    main.add_argument("--upload", action="store_true", default=False,
      help="upload phonebook specified with LOAD to Fritz!Box")
    main.add_argument("--save-cert", dest="save_cert", action="store_true", default=False,
      help="save certificate")
    main.add_argument("--test-access", dest="test_access", action="store_true", default=False,
      help="test access to Fritz!Box")

  # file import
  fileImport = parser.add_argument_group("phonebook load")
  fileImport.add_argument("--load", nargs="+",
    help="load phonebooks from file by name")
  fileImport.add_argument("--country-code", dest="country_code", default="+41",
    help="country code, e.g. +41")
  fileImport.add_argument("--vip-groups", dest="vip_groups", nargs="+", default=["Family"],
    help="vip group names")

  # download from WebDAV server (e.g. Nextcloud)
  downloadWebDAV = parser.add_argument_group("download WebDAV")
  downloadWebDAV.add_argument("--webdav-url", dest="webdav_url", nargs="+",
    help="webdav URL, e.g. https://<HOST>/remote.php/dav/addressbooks/users/<LOGIN>/<BOOK>/")
  downloadWebDAV.add_argument("--webdav-username", dest="webdav_username",
    help="webdav username")
  downloadWebDAV.add_argument("--webdav-password", dest="webdav_password",
    help="webdav password")

  # misc
  misc = parser.add_argument_group("misc")
  misc.add_argument("--save-pictures", dest="save_pictures", action="store_true", default=False,
    help="Save pictures within VCF to local fonpix folder. "
         "The pictures must be uploaded manually to the Fritz!Box NAS (https://fritz.nas path=/fritz.nas/FRITZ/fonpix")

  # upload
  if False:
    upload = parser.add_argument_group("upload")
    upload.add_argument("--hostname", default="https://fritz.box",
      help="hostname")
    upload.add_argument("--password",
      help="password")
    upload.add_argument("--phonebook-id", dest="phonebook_id", default=0,
      help="phonebook id: 0 for main phone book, 1 for next phone book in list, etc...")
    upload.add_argument("--cert-verify", dest="cert_verify", action="store_true", default=False,
      help="do not use certificate to verify secure connection. Default is without certificate")

  args = parser.parse_args()

  picture_path = None
  if args.save_pictures:
    if args.save: picture_path = os.path.dirname(args.save)
    else: picture_path = "."
    picture_path = os.path.join(picture_path, "fonpix")
    print("save pictures to %s" % picture_path)

  try:
    books = None
    if args.load:
      books = fritzbox.phonebook.Phonebooks()
      for f in args.load:
        print("load phonebook from %s" % f)
        ext = os.path.splitext(f)[1].lower()
        if ext == ".csv":
          csv = fritzbox.CSV.Import()
          tmp = csv.get_books(f, args.vip_groups, debug=args.debug)
          books.addPhonebooks(tmp)
        elif ext == ".ldif":
          ldif = fritzbox.LDIF.Import()
          tmp = ldif.get_books(f, args.vip_groups, debug=args.debug)
          books.addPhonebooks(tmp)
        elif ext == ".vcf":
          vcf = fritzbox.VCF.Import()
          tmp = vcf.get_books(f, args.vip_groups, picture_path, debug=args.debug)
          books.addPhonebooks(tmp)
        else:
          print("error: file format not supported '%s'. Supported are *.ldif, *.csv and *.vcf files." % ext)
          sys.exit(-1)
    elif args.webdav_url:
      dav = fritzbox.CardDAV.Import()
      books = fritzbox.phonebook.Phonebooks()
      for url in args.webdav_url:
        print("download phonebook from %s" % url)
        tmp = dav.get_books(url, args.webdav_username, args.webdav_password,
                           args.vip_groups, picture_path, debug=args.debug)
        books.addPhonebooks(tmp)

    # post process
    if books:
      books.normalizeNumbers(args.country_code)
      books.calculateMainNumber()
      books.mergeToOnePhonebook()

    if args.save:
      print("save phonebook to %s" % args.save)
      books.write(args.save)
    elif args.save_cert:
      print("save certificate")
      session = fritzbox.access.Session(args.password, url=args.hostname, cert_verify=args.cert_verify, debug=args.debug)
      session.save_certificate()
    elif args.upload:
      print("upload phonebook to %s" % args.hostname)
      session = fritzbox.access.Session(args.password, url=args.hostname, cert_verify=args.cert_verify, debug=args.debug)
      books.upload(session, args.phonebook_id)
    elif args.test_access:
      print("test access to %s" % args.hostname)
      session = fritzbox.access.Session(args.password, url=args.hostname, cert_verify=args.cert_verify, debug=args.debug)
      session.get_sid()
      print("login worked")
  except Exception as ex:
    print("error: %s" % ex)
    if args.debug:    
      import traceback
      print(traceback.format_exc())
    sys.exit(-2)

