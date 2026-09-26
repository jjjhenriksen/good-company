#!/usr/bin/env python3
"""Check required Linux filesystem syscall support without touching agent state."""
import ctypes
import errno
import json
import os
import platform
import sys


def check():
    result = {'system': platform.system(), 'architecture': platform.machine()}
    if result['system'] != 'Linux' or result['architecture'] not in ('x86_64', 'aarch64'):
        return result | {'ready': False, 'reason': 'Run this preflight inside the release Linux container.'}
    library = ctypes.CDLL(None, use_errno=True)
    # openat2 is syscall 437 on the two supported Linux architectures.
    # Open a directory read-only; no state files or credentials are accessed.
    how = (ctypes.c_uint64 * 3)(os.O_RDONLY | os.O_DIRECTORY, 0, 0)
    ctypes.set_errno(0)
    fd = library.syscall(ctypes.c_long(437), ctypes.c_int(-100), ctypes.c_char_p(b'/tmp'),
                         ctypes.byref(how), ctypes.c_size_t(ctypes.sizeof(how)))
    if fd < 0:
        code = ctypes.get_errno()
        return result | {'ready': False, 'errno': code,
                         'reason': 'Required openat2 syscall is unavailable.' if code == errno.ENOSYS else os.strerror(code),
                         'next': 'Use a compatible Linux runtime; do not disable filesystem containment.'}
    os.close(fd)
    return result | {'ready': True, 'scope': 'Filesystem syscall support only; model, providers and restart remain unverified.'}


if __name__ == '__main__':
    result = check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['ready'] else 2)
