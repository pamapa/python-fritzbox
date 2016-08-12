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

import os, sys, argparse
import urlparse

# fritzbox modules
import fritzbox.phonebook
import fritzbox.access
import fritzbox.CSV
import fritzbox.LDIF


#
# main
#
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Fritz!Box util")
  parser.add_argument('--debug', action='store_true')

  # action
  main = parser.add_mutually_exclusive_group(required=True)
  main.add_argument("--upload", action="store_true", default=False,
    help="upload phonebook specified with INPUT to Fritz!Box")
  main.add_argument("--save",
    help="save phonebook specified with INPUT to local file")
  main.add_argument("--save-cert", dest="save_cert", action="store_true", default=False,
    help="save certificate")
  main.add_argument("--test-access", dest="test_access", action="store_true", default=False,
    help="test access to Fritz!Box")

  # file import
  fileImport = parser.add_argument_group("file import")
  fileImport.add_argument("--input",
    help="input filename")
  fileImport.add_argument("--country-code", dest="country_code", default="+41",
    help="country code, e.g. +41")
  fileImport.add_argument("--vip-groups", dest="vip_groups", nargs="+", default=["Family"],
    help="vip group names")

  # upload
  upload = parser.add_argument_group("upload")
  upload.add_argument("--hostname", default="https://fritz.box",
    help="hostname")
  upload.add_argument("--password",
    help="password")
  upload.add_argument("--phonebook-id", dest="phonebook_id", default=0,
    help="phonebook id")
  upload.add_argument("--no-cert-verify", dest="cert_verify", action="store_false", default=True,
    help="do not use certificate to verify secure connection. Default is with certificate")

  args = parser.parse_args()

  books = None    
  if args.input:
    vipGroups = {}
    for vip_group in args.vip_groups:
      vipGroups[vip_group] = []
    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".ldif":
      ldif = fritzbox.LDIF.Import()
      books = ldif.get_books(args.input, args.country_code, vipGroups, debug=args.debug)
    elif ext == ".csv":
      csv = fritzbox.CSV.Import()
      books = csv.get_books(args.input, args.country_code, debug=args.debug)
    else:
      print("Error: File format not supported '%s'. Supported are LDIF and CSV." % ext)
      sys.exit(-1)

  try:
    if args.save:
      print("save phonebook to %s..." % args.save)
      books.write(args.save)
    elif args.save_cert:
      print("save certificate")
      session = fritzbox.access.Session(args.password, url=args.hostname, usecafile=args.usecafile, debug=args.debug)
      session.save_certificate()
    elif args.upload:
      print("upload phonebook to %s..." % args.hostname)
      session = fritzbox.access.Session(args.password, url=args.hostname, usecafile=args.cert_verify, debug=args.debug)
      books.upload(session, args.phonebook_id)
    elif args.test_access:
      print("test access to %s..." % args.hostname)
      session = fritzbox.access.Session(args.password, url=args.hostname, usecafile=args.cert_verify, debug=args.debug)
      session.get_sid()
      print("Login worked")
  except Exception, ex:
    print("Error: %s" % ex)
    sys.exit(-2)

