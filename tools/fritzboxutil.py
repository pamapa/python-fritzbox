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

# fritzbox module
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

  main = parser.add_mutually_exclusive_group(required=True)
  main.add_argument("--upload", help="upload phonebook to Fritz!Box", action="store_true", default=False)
  main.add_argument("--save", help="save phonebook to filename")
  main.add_argument("--savecafile", help="save certificate", action="store_true", default=False)

  # file import
  fileImport = parser.add_argument_group("file import")
  fileImport.add_argument("--kind", choices=["LDIF", "CSV"], default="LDIF")
  fileImport.add_argument("--input", help="input filename")
  fileImport.add_argument("--country_code", help="country code, e.g. +41", default="+41")
  fileImport.add_argument("--vip_groups", nargs="+", help="vip group names", default=["Family"])

  # upload
  uploadOrCafile = parser.add_argument_group("upload or cafile")
  uploadOrCafile.add_argument("--hostname", help="hostname", default="https://fritz.box:443")
  uploadOrCafile.add_argument("--password", help="password")
  uploadOrCafile.add_argument("--phonebook_id", help="phonebook id", default=0)
  uploadOrCafile.add_argument("--usecafile", help="use stored certificate to verify secure connection", action="store_true", default=True)

  args = parser.parse_args()

  books = None    
  if args.input:
    vipGroups = {}
    for vip_group in args.vip_groups:
      vipGroups[vip_group] = []
    if args.kind == "LDIF":
      ldif = fritzbox.LDIF.Import()
      books = ldif.get_books(args.input, args.country_code, vipGroups, debug=args.debug)
    elif args.kind == "CSV":
      csv = fritzbox.CSV.Import()
      books = csv.get_books(args.input, args.country_code, debug=args.debug)

  if args.save:
    print("save phonebook to %s..." % args.save)
    with open(args.save, "w") as f:
      f.write(str(books))
  elif args.savecafile:
    print("save certificate")
    session = fritzbox.access.Session(args.password, url=args.hostname, usecafile=args.usecafile, debug=args.debug)
    session.save_certificate()
  elif args.upload:
    print("upload phonebook to %s..." % args.hostname)
    session = fritzbox.access.Session(args.password, url=args.hostname, usecafile=args.usecafile, debug=args.debug)
    #print session.get_sid()
    books.upload(session, args.phonebook_id)

