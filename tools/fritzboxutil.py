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

import sys, argparse

# fritzbox module
import fritzbox.phonebook
import fritzbox.access
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
  main.add_argument("--cafile", help="save certificate", action="store_true", default=False)

  # file import
  fileImport = parser.add_argument_group("file import")
  fileImport.add_argument("--kind", choices=["LDIF"], default="LDIF")
  fileImport.add_argument("--input", help="input filename", default="in.ldif")
  fileImport.add_argument("--country_code", help="country code, e.g. +41", default="+41")
  fileImport.add_argument("--vip_groups", nargs="+", help="vip group names", default=["Family"])

  # upload
  upload = parser.add_argument_group("upload")
  upload.add_argument("--hostname", help="hostname", default="https://fritz.box")
  upload.add_argument("--password", help="password")
  upload.add_argument("--phonebookid", help="phonebook id", default=0)

  args = parser.parse_args()

  if args.upload:
    print("upload phonebook to %s..." % args.hostname)
    #session = fritzbox.access.Session(args.password, args.hostname)
    #books.upload(session, args.phonebookid)
  elif args.save:
    print("save phonebook to %s..." % args.save)
    vipGroups = {}
    for vip_group in args.vip_groups:
      vipGroups[vip_group] = []
    books = None    
    if args.kind == "LDIF":
      ldif = fritzbox.LDIF.Import()
      books = ldif.get_books(args.input, args.country_code, vipGroups)
    else:
      print "Error: Unknown kind %s" % args.kind
      sys.exit(-1)
    with open(args.save, "w") as f:
      f.write(str(books))
  elif args.cafile:
    print("save certificate")
    session = fritzbox.access.Session(args.password, url=args.hostname, debug=args.debug)
    session.save_certificate()

