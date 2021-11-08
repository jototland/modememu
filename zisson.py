"""Dialing with Zisson"""
import json
import re

import requests

class ZissonDialer:
    """ZissonDialer provides a method dial() to dial a phone number in E164-format"""
    def __init__(self):
        with open('zisson.json', encoding="utf8") as json_file:
            data = json.load(json_file)

        provider = data['provider'].lower()
        apiuser = data['apiuser']
        apipassword = data['apipassword']
        self._phone = data['phone']

        assert provider in ['kvantel', 'tdc']
        assert isinstance(apiuser, str)
        assert isinstance(apipassword, str)
        assert re.match(r'\+\d+$', self._phone)

        domain = '.com' if provider == 'kvantel' else '.no'
        self._base_url = f'https://api.zisson{domain}/api/simple/'
        self._auth = (apiuser, apipassword)


    def _get(self, path, params):
        response = requests.get(self._base_url + path,
                                params=params,
                                auth=self._auth)
        if response.status_code == 200:
            return response.text
        raise ValueError(response.status_code)


    def dial(self, to_number):
        """dials a phone number in E164 format"""
        params = {'from': self._phone, 'to': to_number}
        result = self._get('Dial', params)
        if result != '1':
            raise RuntimeError(f"Zisson failed to dial '{to_number}'")
