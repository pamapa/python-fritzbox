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
import re
import argparse
import traceback
import logging
import lxml.html
import json

# pip install fritzconnection
from fritzconnection import FritzConnection

URL_DATA = "/data.lua"


# inspired by https://github.com/flopp/fritz-switch-profiles
# tested with FRITZ!Box 5590 using FRITZ!OS:7.58
class FritzboxKidProfile(object):
    def __init__(self, name: str, id: str) -> None:
        self.name = name
        self.id = id
    def __repr__(self) -> str:
        return "%s (id=%s)" % (self.name, self.id)


class FritzboxDevice(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self.network_ids = []
        self.filter_ids = []
    def __repr__(self) -> str:
        return "%s (network_ids=[%s],filter_ids=[%s])" % (self.name, ",".join(self.network_ids), ",".join(self.filter_ids))


class FritzboxFilter(object):
    def __init__(self, fc) -> None:
        self._fc = fc
        self._logger = logging.getLogger()

        self._fc.http_interface._set_sid_from_box()
        self._sid = self._fc.http_interface.sid    
        self._url_data = "%s/%s" % (self._fc.address, URL_DATA)

        self.devices = self._get_devices()
        self.profiles = self._get_profiles()

    def _get_devices(self) -> list[FritzboxDevice]:
        self._logger.debug("_get_devices...")
        ret: list[FritzboxDevice] = []

        # by network
        data = {"xhr": "1", "sid": self._sid, "lang": "de", "page": "netDev", "xhrId": "cleanup", "useajax": "1", "no_sidrenew": ""}
        r = self._fc.session.post(self._url_data, data=data)
        j = json.loads(r.text)
        data = j["data"]
        for d in data["active"] + data["passive"]:
            # merge by name
            for r in ret:
                if r.name == d["name"]:
                    device = r
                    break
            else:
                device = FritzboxDevice(d["name"])
                ret.append(device)
            device.network_ids.append(d["UID"])

        # by filter
        data = {"xhr": 1, "sid": self._sid, "page": "kidLis"}
        r = self._fc.session.post(self._url_data, data=data)
        html = lxml.html.fromstring(r.text)
        for row in html.xpath('//table[@id="uiDevices"]/tr'):
            device_name = row.xpath('td[@class="name"]/span/text()')
            if not device_name:
                continue
            device_name = device_name[0]
            device_uid = row.xpath('td[@class="block"]/a/@data-uid')
            if not device_uid:
                continue
            device_uid = device_uid[0]
            # merge by name
            for r in ret:
                if r.name == device_name:
                    device = r
                    break
            else:
                device = FritzboxDevice(device_name)
                ret.append(device)
            device.filter_ids.append(device_uid)

        return ret

    def get_device_by_name(self, name):
        for device in self.devices:
            if device.name == name:
                return device
        return None

    def get_device_details(self, device_lan_id: str):
        self._logger.debug("get_device_details...")
        data = {"xhr": 1, "sid": self._sid, "lang": "de", "page": "edit_device", "xhrId": "all", "backToPage": "netDev", "dev": device_lan_id}
        r = self._fc.session.post(self._url_data, data=data)
        j = json.loads(r.text)
        kisi = j["data"]["vars"]["dev"]["netAccess"]["kisi"]
        profiles = kisi["profiles"]
        profile_selected = self._get_profile_by_id(profiles["selected"])
        return {"profile_selected": profile_selected}

    def _get_profiles(self) -> list[FritzboxKidProfile]:
        self._logger.debug("_get_profiles...")
        data = {"xhr": 1, "sid": self._sid, "page": "kidPro"}
        r = self._fc.session.post(self._url_data, data=data)
        html = lxml.html.fromstring(r.text)
        ret: list[FritzboxKidProfile] = []
        for row in html.xpath('//table[@id="uiProfileList"]/tr'):
            profile_name = row.xpath('td[@class="name"]/span/text()')
            if not profile_name:
                continue
            profile_name = profile_name[0]
            profile_id = row.xpath('td[@class="btncolumn"]/button[@name="edit"]/@value')[0]
            ret.append(FritzboxKidProfile(profile_name, profile_id))
        return ret
  
    def _get_profile_by_id(self, id):
        for profile in self.profiles:
             if profile.id == id:
                return profile
        return None

    def get_profile_by_name(self, name):
        for profile in self.profiles:
             if profile.name == name:
                return profile
        return None

    def get_profile_details(self, profile: FritzboxKidProfile):
        self._logger.debug("get_profile_details...")
        data = {"xhr": 1, "sid": self._sid, "edit": profile.id, "back_to_page": "kidPro", "page": "kids_profileedit"}
        r = self._fc.session.post(self._url_data, data=data)
        html = lxml.html.fromstring(r.text)
        assigned_devices = []
        for row in html.xpath('//h4[@id="uiUserlistAnchor"][1]/following-sibling::div[@class="formular"]/table/tr'):
            device_name = row.xpath('td/text()')[0]
            device = self.get_device_by_name(device_name)
            assigned_devices.append(device)
        assigned_devices = list(dict.fromkeys(assigned_devices))
        return {"assigned_devices": assigned_devices}

    def set_profiles(self, device_profiles: list[list[str]]):
        self._logger.debug("set_profile...")
        data = {"xhr": 1, "sid": self._sid, "apply": "", "oldpage": "/internet/kids_userlist.lua"}
        updates = 0
        for device_name, profile_name in device_profiles:
            device = self.get_device_by_name(device_name)
            if not device:
                self._logger.error("device '%s' not found" % device_name)
                continue
            profile = self.get_profile_by_name(profile_name)
            if not profile:
                self._logger.error("profile '%s' not found" % profile_name)
                continue
            self._logger.info("set device(s) '%s' to profile '%s'" % (device.name, profile.name))
            for device_id in device.filter_ids:
                updates += 1
                data["profile:%s" % device_id] = profile.id
        if updates != 0:
            self._fc.session.post(self._url_data, data=data)


def parse_argument_kv(s: str):
    if not re.match("^[^=]+=[^=]+$", s):
        raise argparse.ArgumentTypeError("Invalid format: '%s'." % s)
    return s.split("=")


#
# main
#
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manipulate internet filter")
    parser.add_argument("--hostname", default="https://fritz.box",
        help="Hostname")
    parser.add_argument("--username", type=str,
        help="Login username. If not set the environment FRITZ_USERNAME is used.")
    parser.add_argument("--password", type=str,
        help="Login password. If not set the environment FRITZ_PASSWORD is used.")
    # action
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true",
        help="List all available devices and profiles")
    action.add_argument("--list-device", dest="list_device", type=str,
        help="List device(s) by name")
    action.add_argument("--list-profile", dest="list_profile", type=str,
        help="List profile by name")
    action.add_argument("--device-profiles", dest="device_profiles", nargs="*", metavar="DEVICE_NAME=PROFILE_NAME", type=parse_argument_kv,
        help="Set device to profile by name. E.g. DeviceName1=ProfileName1")
    # others
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    # logging
    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h2 = logging.StreamHandler()
    h2.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO, handlers=[h1, h2])
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARN)
    logging.getLogger("fritzconnection").setLevel(logging.WARN)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        fc = FritzConnection(address=args.hostname, use_tls=True, user=args.username, password=args.password)
        filter = FritzboxFilter(fc)
        if args.list:
            print("\nAvailable devices:")
            for d in filter.devices:
                print(d)
            print("\nAvailable profiles:")
            for p in filter.profiles:
                print(p)
        elif args.list_device:
            d = filter.get_device_by_name(args.list_device)
            if d:
                print("\nDevice %s:" % d.name)
                for device_lan_id in d.network_ids:
                    details = filter.get_device_details(device_lan_id)
                    print(" - id=%s" % device_lan_id)
                    print("   - profile_selected=%s" % details["profile_selected"])
            else:
                print("Device %s not found" % args.list_device)
        elif args.list_profile:
            p = filter.get_profile_by_name(args.list_profile)
            if p:
                details = filter.get_profile_details(p)
                print("\nProfile %s:" % p.name)
                print(" - id=%s" % p.id)
                print(" - assigned_devices")
                for d in details["assigned_devices"]:
                  print("   - %s" % d)
            else:
                print("Profile %s not found" % args.list_profile)
        elif args.device_profiles:
            filter.set_profiles(args.device_profiles)
    except Exception as ex:
        logging.error(ex)
        logging.debug(traceback.format_exc())
        sys.exit(-2)
