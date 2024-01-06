# python-fritzbox
Automation scripts for the Fritz!Box by using Python.


## Features

### Phone books
- Convert into Fritz!Box XML format
  - VCARD address books (VCF)
  - Thunderbird address books (LDIF)
  - Various other address book formats (CSV)

### Phone spam blacklist
- Import
  - Blacklists provided as address books (CSV) from tellows (http://www.tellows.com)
- Download phone blacklist from ktipp (https://www.ktipp.ch), which is a phone spam blacklist periodically updated
- Save into Fritz!Box XML format
 

## Tested hardware
Tested with
- Fritzbox 5590


## Install on Debian (bookworm)
```bash
sudo apt-get install python3

git clone https://github.com/pamapa/python-fritzbox.git
cd python-fritzbox
virtualenv -p python3 env
source env/bin/activate
pip install -r requirements.txt
```


## Examples
```bash
# Convert a LDIF address book into Fritz!Box XML format:
fritzboxphonebook.py --load mybook.ldif --save mybook.xml
```
