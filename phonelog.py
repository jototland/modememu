"""Dialing with Phonelog (other project)"""
import json
import logging

import requests

from console_user import console_user_email_and_phone
from e164 import to_e164
from init_serial import init_serial
import modem

class PhoneLogDialer:
    """PhoneLogDialer provides a method dial() to dial a phone number in E164-format"""
    def __init__(self):
        with open('phonelog.json', encoding="utf-8") as json_file:
            data = json.load(json_file)

        self._api_url = f"https://{data['hostname']}/api/dial"
        self._auth = (data['username'], data['password'])
        self._country_code = data.get('country_code', '')
        self._local_code = data.get('local_prefix', '')


    def dial(self, to_number):
        """dials a phone number in E164 format"""
        email, phone_fallback = console_user_email_and_phone(self._country_code,
                                                             self._local_code)
        params = {'operator_email': email,
                  'operator_fallback_number': to_e164(phone_fallback,
                                                      self._country_code,
                                                      self._local_code),
                  'to_number': to_e164(to_number,
                                       self._country_code,
                                       self._local_code)}
        response = requests.post(self._api_url,
                                auth=self._auth,
                                params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Phonelog API returned status code {response.status_code}")
        result = response.text
        if result != 'success\n':
            raise RuntimeError(f"Phonelog failed to dial '{to_number}'")
