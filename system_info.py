from __future__ import annotations
import os, sys, time, platform, subprocess
from typing import Optional, Dict, Tuple

try:
    import psutil
except Exception:
    psutil = None



def start_timers() -> Tuple[float, float]:
    return time.perf_counter(), time.process_time()


def stop_timers(t_wall_start: float, t_cpu_start: float) -> Dict[str, float]:
    return {
        "wall_s": time.perf_counter() - t_wall_start,
        "cpu_s":  time.process_time() - t_cpu_start,
    }



def _cpu_model_fallback() -> Optional[str]:
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    # macOS
    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"]
            ).decode(errors="ignore").strip()
            if out:
                return out
    except Exception:
        pass
    # Windows / generic
    try:
        cpu = platform.processor()
        if cpu:
            return cpu
    except Exception:
        pass
    try:
        return platform.uname().processor or None
    except Exception:
        return None


def get_cpu_info() -> Dict[str, object]:
    return {
        "model": _cpu_model_fallback(),
        "cores_logical": os.cpu_count(),
    }


def _ram_total_bytes_psutil() -> Optional[int]:
    if psutil is None:
        return None
    try:
        return int(psutil.virtual_memory().total)
    except Exception:
        return None


def _ram_total_bytes_linux() -> Optional[int]:
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("MemTotal:"):

                        parts = line.split()
                        kb = int(parts[1])
                        return kb * 1024
    except Exception:
        pass
    return None


def _ram_total_bytes_macos() -> Optional[int]:
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
        return int(out)
    except Exception:
        return None


def _ram_total_bytes_windows() -> Optional[int]:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)) == 0:
            return None
        return int(stat.ullTotalPhys)
    except Exception:
        return None


def get_ram_info() -> Dict[str, Optional[int]]:
    total = _ram_total_bytes_psutil()
    if total is None:
        if sys.platform.startswith("linux"):
            total = _ram_total_bytes_linux()
        elif sys.platform == "darwin":
            total = _ram_total_bytes_macos()
        elif os.name == "nt":
            total = _ram_total_bytes_windows()
    return {"total_bytes": total}



def get_system_info() -> Dict[str, object]:
    cpu = get_cpu_info()
    ram = get_ram_info()
    return {
        "cpu_model": cpu.get("model"),
        "cpu_cores_logical": cpu.get("cores_logical"),
        "ram_total_bytes": ram.get("total_bytes"),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def pretty_print_summary(timings: Dict[str, float], system: Dict[str, object]) -> None:
    wall = timings.get("wall_s", 0.0)
    cpu  = timings.get("cpu_s", 0.0)
    print(f"Elapsed wall time: {wall:.3f} s")
    print(f"CPU time:          {cpu:.3f} s")

    cpu_model = system.get("cpu_model")
    cores     = system.get("cpu_cores_logical")
    if cpu_model:
        print(f"CPU: {cpu_model} (logical cores: {cores})")
    ram_bytes = system.get("ram_total_bytes")
    if isinstance(ram_bytes, (int, float)) and ram_bytes > 0:
        print(f"RAM total: {ram_bytes / (1024**3):.2f} GiB")

    print(f"Python: {system.get('python')}  |  Platform: {system.get('platform')}")
