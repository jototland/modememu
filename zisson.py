import requests
import json
import re

class ZissonDialer:
    def __init__(self, jsonfile):
        with open('zisson.json') as f:
            data = json.load(f)

        provider = data['provider'].lower()
        apiuser = data['apiuser']
        apipassword = data['apipassword']
        self._phone = data['phone']

        assert provider in ['kvantel', 'tdc']
        assert type(apiuser) == str
        assert type(apipassword) == str
        assert re.match('\+\d+$', self._phone)

        domain = '.com' if provider == 'kvantel' else '.no'
        self._base_url = f'https://api.zisson{domain}/api/simple/'
        self._auth = (apiuser, apipassword)


    def _q(self, s, params):
        response = requests.get(self._base_url + s,
                                params=params,
                                auth=self._auth)
        if response.status_code == 200:
            return response.text
        else:
            raise ValueError(response.status_code)


    def dial(self, to):
        params = {'from': self._phone, 'to': to}
        result = self._q('Dial', params)
        if result != '1':
            raise Error('dial failed')




if __name__ == "__main__":
    import logging
    import http.client as http_client
    import sys
    number = sys.argv[1]
    assert re.match('\+\d+$', number)
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    zisson = Zisson('zisson.json')
    result = zisson.dial('+4792832354')
    print(result)
