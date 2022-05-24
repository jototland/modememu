from collections import namedtuple
import os
import subprocess

import active_directory as ad


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


def console_user_email():
    return user2email(console_user())


if __name__ == "__main__":
    print(f"Email address of the console user is {console_user_email()}")
