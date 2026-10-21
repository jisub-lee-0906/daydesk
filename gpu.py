"""Read the installed NVIDIA driver without spawning nvidia-smi or creating CUDA contexts."""
import ctypes as C
import os
from pathlib import Path


class MemoryV1(C.Structure):
    _fields_ = [('total', C.c_ulonglong), ('free', C.c_ulonglong), ('used', C.c_ulonglong)]


class MemoryV2(C.Structure):
    _fields_ = [('version', C.c_uint), ('total', C.c_ulonglong), ('reserved', C.c_ulonglong), ('free', C.c_ulonglong), ('used', C.c_ulonglong)]


class Utilization(C.Structure):
    _fields_ = [('gpu', C.c_uint), ('memory', C.c_uint)]


class GpuMonitor:
    def __init__(self):
        self.lib = None
        self.devices = []
        try:
            dll = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'nvml.dll'
            lib = C.CDLL(str(dll))
            declarations = {
                'nvmlInit_v2': ([], C.c_int), 'nvmlShutdown': ([], C.c_int),
                'nvmlDeviceGetCount_v2': ([C.POINTER(C.c_uint)], C.c_int),
                'nvmlDeviceGetHandleByIndex_v2': ([C.c_uint, C.POINTER(C.c_void_p)], C.c_int),
                'nvmlDeviceGetName': ([C.c_void_p, C.c_char_p, C.c_uint], C.c_int),
                'nvmlDeviceGetMemoryInfo': ([C.c_void_p, C.POINTER(MemoryV1)], C.c_int),
                'nvmlDeviceGetUtilizationRates': ([C.c_void_p, C.POINTER(Utilization)], C.c_int),
                'nvmlDeviceGetTemperature': ([C.c_void_p, C.c_uint, C.POINTER(C.c_uint)], C.c_int),
            }
            for name, (args, result) in declarations.items():
                fn = getattr(lib, name)
                fn.argtypes, fn.restype = args, result
            if hasattr(lib, 'nvmlDeviceGetMemoryInfo_v2'):
                lib.nvmlDeviceGetMemoryInfo_v2.argtypes = [C.c_void_p, C.POINTER(MemoryV2)]
                lib.nvmlDeviceGetMemoryInfo_v2.restype = C.c_int
            if lib.nvmlInit_v2() != 0:
                return
            self.lib = lib
            count = C.c_uint()
            if lib.nvmlDeviceGetCount_v2(C.byref(count)) == 0:
                for i in range(min(count.value, 16)):
                    handle = C.c_void_p()
                    if lib.nvmlDeviceGetHandleByIndex_v2(i, C.byref(handle)) == 0:
                        name = C.create_string_buffer(128)
                        lib.nvmlDeviceGetName(handle, name, 128)
                        self.devices.append((i, handle, name.value.decode('utf-8', errors='replace') or 'NVIDIA GPU'))
        except (OSError, AttributeError):
            self.close()

    def sample(self):
        if not self.lib:
            return []
        result = []
        for index, handle, name in self.devices:
            memory = None
            if hasattr(self.lib, 'nvmlDeviceGetMemoryInfo_v2'):
                raw = MemoryV2()
                raw.version = C.sizeof(raw) | (2 << 24)
                if self.lib.nvmlDeviceGetMemoryInfo_v2(handle, C.byref(raw)) == 0 and raw.total:
                    memory = {'total': raw.total, 'used': raw.used, 'free': raw.free, 'reserved': raw.reserved, 'source': 'NVML v2'}
            if memory is None:
                raw = MemoryV1()
                if self.lib.nvmlDeviceGetMemoryInfo(handle, C.byref(raw)) == 0 and raw.total:
                    memory = {'total': raw.total, 'used': raw.used, 'free': raw.free, 'reserved': None, 'source': 'NVML'}
            usage, temp = Utilization(), C.c_uint()
            utilization = usage.gpu if self.lib.nvmlDeviceGetUtilizationRates(handle, C.byref(usage)) == 0 else None
            temperature = temp.value if self.lib.nvmlDeviceGetTemperature(handle, 0, C.byref(temp)) == 0 else None
            result.append({'index': index, 'name': name, 'memory': memory, 'utilization': utilization, 'temperature': temperature})
        return result

    def close(self):
        if self.lib:
            self.lib.nvmlShutdown()
            self.lib = None
            self.devices = []
