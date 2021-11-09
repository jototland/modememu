import sys
import time
import win32api
import threading

def _ctrl_c_handler(signal, func=None):
    if signal == 0: # ctrl+c
        print('Ctrl+C pressed. Exiting...')
        sys.exit(1)
    return 1


def install_ctrl_c_handler():
    win32api.SetConsoleCtrlHandler(_ctrl_c_handler, True)

if __name__ == "__main__":
    def work():
        time.sleep(1000000)


    t = threading.Thread(target=work)
    t.daemon=True
    t.start()

    install_ctrl_c_handler()
    t.join()

