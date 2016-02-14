# python-fritzbox
Automated the Fritz!Box by using python.


## Install on Debian (jessie)
```bash
sudo apt-get install python python-beautifulsoup python-ldap

# Add to PYTHONPATH
# TODO: explain

# Fritz!Box is using own signed certificate,
# download it locally to verify it when connecting
fritzboxutil.py --cafile
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

