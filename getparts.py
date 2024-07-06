'''
Python3

API tool for electronic component suppliers (digikey, mouser, LCSC)
https://github.com/maholli/getparts
M.Holliday
'''

import requests
import json, re
import os.path 
from os import path
from types import SimpleNamespace


mouser_headers = {
    'Content-Type': "application/json",
    'accept': "application/json"
}

def printlevel(level,text):
    print('\t'*level+str(text))

class API:
    RECORDS_FILE = 'api_records_digi.txt'
    def __init__(self,cred,debug=False):
        self.DEBUG=debug
        self.mouserPN="https://api.mouser.com/api/v1/search/partnumber?apiKey=".encode('utf-8')
        self.barcode=SimpleNamespace()
        self.query=SimpleNamespace()
        self.query.suppliers={
            'mouser':{
                '1D':lambda:print('mouser1d'),
                '2D':lambda:requests.post(url=self.mouserPN+cred['mouser_key'].encode('utf-8'),data=self.barcode.mfpn.encode(), headers=mouser_headers),
            }
        }

    def search(self,scan,product_info=False):
        # Determine barcode type and supplier
        self.barcode.barcode=scan.data
        if self.DEBUG: print(scan)
        try:
            if 'QRCODE' in scan.type:
                print("isqr")
                self.barcode.type='2D'
                self.barcode.supplier='lcsc'
                supPN=re.split(r",",self.barcode.barcode.decode())
                self.barcode.supplierPN=supPN[1][12:]
            elif 'CODE128' in scan.type:
                print("is128")
                self.barcode.type='1D'
                if self.barcode.barcode.decode().isdecimal():
                    if len(self.barcode.barcode) > 10:
                        self.barcode.supplier='digikey'
                    else:
                        print("Short barcode... possibly Mouser Line Item or QTY: ".format(self.barcode.barcode.decode()))
                else:
                    self.barcode.supplier='mouser'
            else:
                print('Unknown supplier')
        except AttributeError:
            self.barcode.type='2D'
            if b'[)>' in self.barcode.barcode:
                self.barcode.supplier='mouser'
                mfgpart=re.split(r"",self.barcode.barcode.decode())
                print('mfgpart:',mfgpart)
                if '1P' in mfgpart[3]:
                    self.barcode.mfpn="{\"SearchByPartRequest\": {\"mouserPartNumber\": \""+mfgpart[3][2:]+"\",}}"
            else:
                self.barcode.supplier='digikey'

        # make supplier-specific API query 
        try:
            r=self.query.suppliers[self.barcode.supplier][self.barcode.type]()
            self.barcode.response=r.json()
            if 'ErrorMessage' in self.barcode.response:
                if 'Bearer token  expired' in self.barcode.response['ErrorMessage']:
                    if self.refresh_token():
                        r=self.query.suppliers[self.barcode.supplier][self.barcode.type]()
                        self.barcode.response=r.json()
                    else:
                        print('Fatal error during token refresh ')
                        return
            if product_info:
                self.barcode.type='pn'
                try:
                    r=self.query.suppliers[self.barcode.supplier][self.barcode.type]()
                    self.barcode.response.update(r.json())
                except Exception as e:
                    print('Error during Product Info request:',e)
            print(json.dumps(self.barcode.response,indent=3,sort_keys=True))
            return self.barcode
        except Exception as e:
            print('Error during API request:',e)
            if self.DEBUG:print('Attributes: {}'.format(self.barcode))
            return
