"""Small Windows API sampler: no subprocesses, WMI, drivers, or external libraries."""
import ctypes as C
from ctypes import wintypes as W
import os

APP_NAMES = {
    'codex': ('Codex', {'codex.exe'}),
    'opencodex': ('OpenCodex', {'ocx.exe', 'opencodex.exe'}),
    'antigravity': ('Antigravity', {'antigravity.exe'}),
    'comfyui': ('ComfyUI', {'comfyui.exe'}),
    'blender': ('Blender', {'blender.exe'}),
    'resolve': ('DaVinci Resolve', {'resolve.exe'}),
    'reaper': ('REAPER', {'reaper.exe'}),
    'ollama': ('Ollama', {'ollama.exe', 'ollama app.exe'}),
    'discord': ('Discord', {'discord.exe'}),
    'browser': ('브라우저 전체', {'chrome.exe', 'msedge.exe', 'firefox.exe', 'brave.exe'}),
}


class MemoryStatus(C.Structure):
    _fields_ = [('length', W.DWORD), ('load', W.DWORD)] + [(x, C.c_ulonglong) for x in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]


class ProcessEntry(C.Structure):
    _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('pid', W.DWORD), ('heap', C.c_size_t), ('module', W.DWORD), ('threads', W.DWORD), ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD), ('exe', W.WCHAR * 260)]


class ProcessMemory(C.Structure):
    _fields_ = [('size', W.DWORD), ('faults', W.DWORD)] + [(x, C.c_size_t) for x in ('peak', 'working', 'quota_peak_paged', 'quota_paged', 'quota_peak_nonpaged', 'quota_nonpaged', 'pagefile', 'peak_pagefile')]


class WindowsMonitor:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('이 수집기는 Windows 전용입니다.')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        self.ps = C.WinDLL('psapi', use_last_error=True)
        declarations = {
            'GlobalMemoryStatusEx': ([C.POINTER(MemoryStatus)], W.BOOL),
            'GetSystemTimes': ([C.POINTER(W.FILETIME)] * 3, W.BOOL),
            'GetDiskFreeSpaceExW': ([W.LPCWSTR] + [C.POINTER(C.c_ulonglong)] * 3, W.BOOL),
            'GetDriveTypeW': ([W.LPCWSTR], W.UINT),
            'GetTickCount64': ([], C.c_ulonglong),
            'CreateToolhelp32Snapshot': ([W.DWORD, W.DWORD], W.HANDLE),
            'Process32FirstW': ([W.HANDLE, C.POINTER(ProcessEntry)], W.BOOL),
            'Process32NextW': ([W.HANDLE, C.POINTER(ProcessEntry)], W.BOOL),
            'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            'CloseHandle': ([W.HANDLE], W.BOOL),
            'GetCurrentProcess': ([], W.HANDLE),
        }
        for name, (args, result) in declarations.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        self.ps.GetProcessMemoryInfo.argtypes = [W.HANDLE, C.POINTER(ProcessMemory), W.DWORD]
        self.ps.GetProcessMemoryInfo.restype = W.BOOL
        self.last_cpu = None

    def memory_for_handle(self, handle):
        data = ProcessMemory()
        data.size = C.sizeof(data)
        return data.working if self.ps.GetProcessMemoryInfo(handle, C.byref(data), data.size) else None

    def own_memory(self):
        return self.memory_for_handle(self.k.GetCurrentProcess())

    def sample(self):
        memory = MemoryStatus()
        memory.length = C.sizeof(memory)
        ram = None
        if self.k.GlobalMemoryStatusEx(C.byref(memory)):
            ram = {'total': memory.total, 'used': memory.total - memory.available, 'percent': round(100 * (memory.total - memory.available) / memory.total, 1)}
        idle, kernel, user = W.FILETIME(), W.FILETIME(), W.FILETIME()
        cpu = None
        if self.k.GetSystemTimes(C.byref(idle), C.byref(kernel), C.byref(user)):
            def integer(v):
                return (v.dwHighDateTime << 32) | v.dwLowDateTime
            current = (integer(idle), integer(kernel) + integer(user))
            if self.last_cpu:
                total = current[1] - self.last_cpu[1]
                if total > 0:
                    cpu = round(max(0, min(100, 100 * (1 - (current[0] - self.last_cpu[0]) / total))), 1)
            self.last_cpu = current
        disk = None
        root = os.environ.get('SystemDrive', 'C:') + '\\'
        if self.k.GetDriveTypeW(root) == 3:
            free, total, physical_free = C.c_ulonglong(), C.c_ulonglong(), C.c_ulonglong()
            if self.k.GetDiskFreeSpaceExW(root, C.byref(free), C.byref(total), C.byref(physical_free)) and total.value:
                disk = {'name': root[:2], 'total': total.value, 'free': physical_free.value, 'percent': round(100 * (total.value - physical_free.value) / total.value, 1)}
        return {'cpu_percent': cpu, 'memory': ram, 'disk': disk, 'uptime_seconds': self.k.GetTickCount64() // 1000, 'collector_bytes': self.own_memory()}

    def apps(self):
        snapshot = self.k.CreateToolhelp32Snapshot(2, 0)
        if snapshot in (None, C.c_void_p(-1).value):
            return None
        groups = {key: {'id': key, 'name': label, 'count': 0, 'memory_bytes': 0, 'memory_complete': True} for key, (label, _) in APP_NAMES.items()}
        entry = ProcessEntry()
        entry.size = C.sizeof(entry)
        try:
            more = self.k.Process32FirstW(snapshot, C.byref(entry))
            if not more:
                return None
            while more:
                name = entry.exe.lower()
                for key, (_, names) in APP_NAMES.items():
                    if name in names:
                        group = groups[key]
                        group['count'] += 1
                        handle = self.k.OpenProcess(0x1000, False, entry.pid)
                        amount = None
                        if handle:
                            try:
                                amount = self.memory_for_handle(handle)
                            finally:
                                self.k.CloseHandle(handle)
                        if amount is None:
                            group['memory_complete'] = False
                        else:
                            group['memory_bytes'] += amount
                more = self.k.Process32NextW(snapshot, C.byref(entry))
        finally:
            self.k.CloseHandle(snapshot)
        return [g for g in groups.values() if g['count'] or g['id'] in ('codex', 'opencodex')]
