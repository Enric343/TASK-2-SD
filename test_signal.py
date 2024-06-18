import os
import signal
import subprocess
import sys
import time


project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
server_script_path = os.path.join(project_dir, 'centralized.py')
server_process = subprocess.Popen([sys.executable, server_script_path])


print(signal.valid_signals())


time.sleep(3)
print("Killing")


server_process.kill()
time.sleep(2)