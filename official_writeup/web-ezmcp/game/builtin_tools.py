from time import time
from typing import List
import subprocess
from simpleeval import simple_eval

try:
    with open("/flag1", "r") as f:
        FLAG1 = f.read().strip()
except Exception:
    FLAG1 = "fake{test_flag_one}"

try:
    with open("/flag2", "rb") as f:
        FLAG2 = f.read().strip()
        FLAG2 = "fake{not_so_easy}"
except Exception:
    FLAG2 = "fake{test_flag_two}"


cmd_whitelist = [
    "ls",
    "pwd",
]


def system(cmd: str, params: List[str], *, check=True):
    print(f"[Builtin]:system\n  cmd: {cmd}\n  params: {params}\n  check: {check}")
    if check and cmd not in cmd_whitelist:
        raise ValueError(f"Command '{cmd}' is not in the whitelist.")
    result = subprocess.run([cmd] + params, capture_output=True, text=True)
    print(f"[Builtin]:system result: {result}")
    return f"exit code: {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"


def merge(src, dst):
    for k, v in src.items():
        if hasattr(dst, "get"):
            if dst.get(k) and isinstance(v, dict):
                merge(v, dst.get(k))
            else:
                dst[k] = v
        elif hasattr(dst, k) and isinstance(v, dict):
            merge(v, getattr(dst, k))
        else:
            setattr(dst, k, v)


class LocalVariables:
    def __init__(self):
        super().__init__()
        self.now = time()
        self.flag1 = FLAG1
        self.flag2 = FLAG2

    def __getitem__(self, key):
        return getattr(self, key)


def eval(code: str, variables: dict):
    print(f"[Builtin]:eval\n  code: {code}\n  variables: {variables}")
    local_vars = LocalVariables()
    merge(variables, local_vars)
    result = simple_eval(code, names=local_vars)
    print(f"[Builtin]:eval result: {result}")
    return str(result)
