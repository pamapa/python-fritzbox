# python-fritzbox
Automate the Fritz!Box by using python.


## Install on Debian (jessie)
```bash
su root
apt-get install python python-setuptools python-beautifulsoup python-ldap 

git clone https://github.com/pamapa/python-fritzbox.git
cd python-fritzbox

# install in files under at /usr/local/lib/python2.7/dist-packages/
# and script links at /usr/local/bin
python setup.py install

# Fritz!Box is using its own signed certificate. The certificate is used to verify the
# secure connection to the Fritz!Box.
# This command will download and store the certificate to /etc/ssl/localcerts.
fritzboxutil.py --savecafile
```


## Tools
- fritzboxutil.py: Import phonebooks, ...
 - Import
  - Thunderbird address books
 - Save in Fritz!Box XML format
 - Upload to Fritz!Box

- firtzboxktipp.py: Download phone blacklist from ktipp
 - Save in Fritz!Box XML format
 - Upload to Fritz!Box
 

## Tested hardware
Tested with
- Fritzbox 7390

