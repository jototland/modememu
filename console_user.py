from collections import namedtuple
import os
import subprocess

import active_directory as ad
from e164 import to_e164


systemroot = os.getenv('SystemRoot', 'C:\\Windows')
query_exe = os.path.join(systemroot, 'system32', 'query.exe')


QueryUserOutput = namedtuple(
    'QueryUserOutput',
    ['username', 'sessionname', 'id', 'state', 'idle_time', 'logon_date', 'logon_time']
)


def console_user():
    """Returns the samAccountName of the user currently logged into the console"""
    process = subprocess.Popen(['query.exe','user'],
                               creationflags=subprocess.CREATE_NO_WINDOW,
                               stdout=subprocess.PIPE)
    result = process.communicate()
    stdout = result[0].decode(encoding='cp65001')
    lines = [line for line in stdout.split('\r\n') if line != '']
    for line in lines[1:]:
        session = QueryUserOutput(*line[1:].split())
        if session.state == 'Active':
            return session.username
    return None


def user2email(user):
    """Returns the email address of `user` from active directory, or None"""
    try:
        return ad.find_user(user).mail
    except:
        return None


def user2phone(user, country_code='', local_code=''):
    """Returns the phone number of `user` from active directory, or None"""
    try:
        return to_e164(ad.find_user(user).telephoneNumber,
                       country_code,
                       local_code)
    except:
        return None


def console_user_email():
    return user2email(console_user())


def console_user_phone(country_code='', local_code=''):
    return user2phone(console_user(), country_code, local_code)


def console_user_email_and_phone(country_code='', local_code=''):
    user = console_user()
    return user2email(user), user2phone(user, country_code, local_code)


if __name__ == "__main__":
    print(f"Email address and phone of the console user is {console_user_email_and_phone()}")
