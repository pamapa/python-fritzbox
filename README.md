# python-fritzbox
Automate the Fritz!Box by using Python.


## Features

### Phone books
- Import
  - VCARD address books (VCF)
  - Thunderbird address books (LDIF)
  - Various other address book formats (CSV)
- Download
  - From CardDAV servers using SabreDAV (Nextcloud, ...)
- Save into Fritz!Box XML format for manual upload
- Upload imported address book to the Fritz!Box

### Phone spam blacklist
- Import
  - Blacklists provided as address books (CSV) from tellows (http://www.tellows.com)
- Download phone blacklist from ktipp (https://www.ktipp.ch), which is a phone spam blacklist periodically updated
- Save into Fritz!Box XML format for manual upload
- Upload fetched address book directly to the Fritz!Box
 

## Tested hardware
Tested with
- Fritzbox 7390


## Install on Debian (bookworm)
```bash
sudo apt-get install python3 python3-ldap python3-vobject python3-bs4 python3-setuptools python3-pil

git clone https://github.com/pamapa/python-fritzbox.git
cd python-fritzbox

# This will install the files in /usr/local/lib/python3.5/dist-packages/
# and add links in /usr/local/bin
sudo python setup.py install

# For experts: instead of installing you can also make use of PYTHONHOME
# by pointing to the "python-fritzbox" folder.

# Fritz!Box is using its own signed certificate. The certificate is used to verify the
# secure connection to the Fritz!Box.
# This command will download and store the certificate to /etc/ssl/localcerts.
sudo fritzboxphonebook.py --save-cert
```


## Examples
```bash
# Convert a LDIF address book into Fritz!Box XML format:
fritzboxphonebook.py --load mybook.ldif --save mybook.xml

# Download CardDAV and convert into Fritz!Box XML format
fritzboxphonebook.py --webdav-url <YOUR URL> --webdav-username <USERNAME> --webdav-password <YOUR PASSWORD> \
                     --save mybook.xml

# Automatically upload a LDIF address book to the Fritz!Box
# phonebook-id: 0=main phone book, 1=next phone book in list
fritzboxphonebook.py --load mybook.ldif \
                     --upload --hostname "https://fritz.box" --phonebook-id 1 --password <YOUR PASSWORD>
```

