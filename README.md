# python-fritzbox
Automate the Fritz!Box by using python.


## Install on Debian (jessie)
```bash
sudo apt-get install python python-setuptools python-beautifulsoup python-ldap python-requests python-vobject

git clone https://github.com/pamapa/python-fritzbox.git
cd python-fritzbox

# This will install the files in /usr/local/lib/python2.7/dist-packages/
# and add links in /usr/local/bin
python setup.py install

# For experts: instead of installing you can also make use of PYTHONHOME
# by pointing to the "python-fritzbox" folder.

# Fritz!Box is using its own signed certificate. The certificate is used to verify the
# secure connection to the Fritz!Box.
# This command will download and store the certificate to /etc/ssl/localcerts.
fritzboxutil.py --save-cert
```


## Tools

### fritzboxutil.py
Import phonebooks
- Import
 - Thunderbird address books (LDIF)
 - Various other address book formats (CSV)
 - Blacklists provied as address books from tellows (http://www.tellows.com)
- Save into Fritz!Box XML format for manual upload
- Upload import directly to Fritz!Box

### fritzboxktipp.py
Download phone blacklist from ktipp (https://www.ktipp.ch), which is a phone spam blacklist periodically updated
- Save into Fritz!Box XML format for manual upload
- Upload directly to Fritz!Box
 

## Tested hardware
Tested with
- Fritzbox 7390

