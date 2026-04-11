#!/usr/bin/env python3
"""
DAN Web daemon.
Usage:
  python3 daemon.py        # start (daemonized)
  python3 daemon.py stop    # stop
  python3 daemon.py run    # run in foreground
"""
import os, sys, signal, atexit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIDFILE = '/tmp/dan_web.pid'
LOGFILE = '/tmp/dan_web.log'
PORT = 3847

def write_pid():
    with open(PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid():
    try: os.unlink(PIDFILE)
    except: pass

def start():
    pid = os.fork()
    if pid > 0:
        print(f'DAN Web starting at http://localhost:{PORT}')
        print(f'PID={pid} → {PIDFILE}')
        return
    os.setsid()
    os.chdir('/')
    sys.stdout.flush(); sys.stderr.flush()
    with open(LOGFILE, 'w') as f:
        os.dup2(f.fileno(), 1)
        os.dup2(f.fileno(), 2)
    atexit.register(remove_pid)
    write_pid()
    run()

def stop():
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f'Stopped PID {pid}')
    except FileNotFoundError:
        print('PID file not found, is the server running?')
    except ProcessLookupError:
        print('Process not found, cleaning up')
        remove_pid()

def run():
    sys.path.insert(0, os.path.join(BASE_DIR, 'server'))
    os.chdir(BASE_DIR)
    from app import app
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='info')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stop':
        stop()
    elif len(sys.argv) > 1 and sys.argv[1] == 'run':
        run()
    else:
        start()
