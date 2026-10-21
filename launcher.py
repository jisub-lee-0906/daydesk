"""Task-local start/stop helper. No service, startup, or system configuration."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser

from server import APP_ID, ROOT

PORT = 8765
URL = f'http://127.0.0.1:{PORT}/'
RUN = ROOT / '.run'


def windows_kernel():
    kernel = C.WinDLL('kernel32', use_last_error=True)
    declarations = {
        'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        'QueryFullProcessImageNameW': ([W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL),
        'GetProcessTimes': ([W.HANDLE] + [C.POINTER(W.FILETIME)] * 4, W.BOOL),
        'TerminateProcess': ([W.HANDLE, W.UINT], W.BOOL),
        'CloseHandle': ([W.HANDLE], W.BOOL),
    }
    for name, (args, result) in declarations.items():
        fn = getattr(kernel, name)
        fn.argtypes, fn.restype = args, result
    return kernel


def creation_ticks(kernel, handle):
    created, exited, system, user = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
    if not kernel.GetProcessTimes(handle, C.byref(created), C.byref(exited), C.byref(system), C.byref(user)):
        raise RuntimeError('프로세스 생성 시각을 확인할 수 없어요.')
    return (created.dwHighDateTime << 32) | created.dwLowDateTime


def health():
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=0.5)
    try:
        connection.request('GET', '/api/health')
        response = connection.getresponse()
        data = json.loads(response.read(4096))
        return data if response.status == 200 and data.get('app') == APP_ID else None
    except (OSError, ValueError, http.client.HTTPException):
        return None
    finally:
        connection.close()


def start(open_browser=True):
    if health():
        if open_browser:
            webbrowser.open(URL)
        print(URL)
        return
    RUN.mkdir(exist_ok=True)
    with (RUN / 'server.log').open('ab') as log:
        child = subprocess.Popen([sys.executable, '-X', 'utf8', '-B', str(ROOT / 'server.py')], cwd=ROOT, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(40):
        data = health()
        if data:
            # A racing launcher can lose the bind; never overwrite ownership for a different PID.
            if data['pid'] == child.pid:
                kernel = windows_kernel()
                handle = kernel.OpenProcess(0x1000, False, child.pid)
                if not handle:
                    raise RuntimeError('시작한 프로세스의 소유권을 기록할 수 없어요.')
                try:
                    created = creation_ticks(kernel, handle)
                    if child.poll() is not None:
                        raise RuntimeError('시작한 수집기가 종료되었어요.')
                finally:
                    kernel.CloseHandle(handle)
                (RUN / 'instance.json').write_text(json.dumps({'app': APP_ID, 'pid': child.pid, 'created_ticks': created, 'started_at': time.time()}), encoding='utf-8')
            if open_browser:
                webbrowser.open(URL)
            print(URL)
            return
        if child.poll() is not None:
            raise RuntimeError(f'8765 포트를 확인해 주세요. 실행 로그: {RUN / "server.log"}')
        time.sleep(0.15)
    raise RuntimeError(f'시작 확인 시간이 지났어요. 같은 프로세스의 로그를 확인해 주세요: {RUN / "server.log"}')


def stop():
    data = health()
    if not data:
        print('실행 중인 이 대시보드가 없어요.')
        return
    record = json.loads((RUN / 'instance.json').read_text(encoding='utf-8'))
    if record.get('app') != APP_ID or record.get('pid') != data.get('pid'):
        raise RuntimeError('이 실행기가 시작한 프로세스인지 확인할 수 없어 종료하지 않았어요.')
    kernel = windows_kernel()
    handle = kernel.OpenProcess(0x1001, False, data['pid'])
    if not handle:
        raise RuntimeError('프로세스에 접근할 수 없어요.')
    try:
        if record.get('created_ticks') != creation_ticks(kernel, handle):
            raise RuntimeError('프로세스 생성 시각이 달라 종료하지 않았어요.')
        buffer, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, C.byref(size)) or Path(buffer.value).resolve() != Path(sys.executable).resolve():
            raise RuntimeError('실행 파일이 달라 종료하지 않았어요.')
        if not kernel.TerminateProcess(handle, 0):
            raise RuntimeError('대시보드 종료에 실패했어요.')
    finally:
        kernel.CloseHandle(handle)
    (RUN / 'instance.json').unlink(missing_ok=True)
    print('대시보드 수집기를 종료했어요. 브라우저 탭은 닫아도 됩니다.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        start(not args.no_browser) if args.action == 'start' else stop()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
