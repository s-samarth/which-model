"""Hardware probe snippet library and pasted-output parser.

Snippets live in data/hardware_snippets.yaml; the agent selects an id, the app
renders the command. The parser turns whatever the user pastes back into a
Hardware object, tolerating partial or mangled output.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from whichmodel.schemas import Hardware


@dataclass(frozen=True)
class Snippet:
    id: str
    os: str
    label: str
    command: str
    explanation: str


@lru_cache
def load_snippets(path: Path) -> dict[str, Snippet]:
    raw = yaml.safe_load(path.read_text())["snippets"]
    return {
        sid: Snippet(id=sid, os=s["os"], label=s["label"],
                     command=s["command"].strip(), explanation=s["explanation"].strip())
        for sid, s in raw.items()
    }


def snippet_for_os(path: Path, os_name: str | None) -> Snippet:
    """Pick the probe snippet for a user's OS; default to macOS (primary audience)."""
    snippets = load_snippets(path)
    key = f"{(os_name or 'macos').lower()}_system"
    return snippets.get(key, snippets["macos_system"])


_GPU_WORDS = r"(GeForce|Radeon|Arc|Iris|UHD|NVIDIA|Quadro)"
_PATTERNS: dict[str, re.Pattern] = {
    "mac_chip": re.compile(r"Chip:\s*(Apple\s+M\d+\s*\w*)", re.I),
    "mac_mem": re.compile(r"Memory:\s*(\d+)\s*GB", re.I),
    "memsize": re.compile(r"hw\.memsize:\s*(\d{9,})"),
    "free_g": re.compile(r"^Mem:\s+(\d+)", re.M),
    "nvidia_csv": re.compile(r"([^,\n]*(?:NVIDIA|GeForce|RTX)[^,\n]*),\s*(\d+)\s*MiB", re.I),
    "lspci_vga": re.compile(r"(?:VGA compatible|3D) controller:\s*([^\n(]+)", re.I),
    "win_mem": re.compile(r"TotalPhysicalMemory\s*-*\s*(\d{9,})"),
    # PowerShell table row: "<gpu name>   <AdapterRAM bytes>"
    "win_gpu_line": re.compile(
        rf"^([A-Za-z][A-Za-z0-9 .()-]*{_GPU_WORDS}[A-Za-z0-9 .()-]*?)\s+(\d{{9,}})\s*$", re.M),
    "win_gpu_name": re.compile(rf"^((?!Name)[A-Za-z][A-Za-z0-9 .()-]*{_GPU_WORDS}[A-Za-z0-9 .-]*)$",
                               re.M),
    "uname": re.compile(r"^(Linux|Darwin)\b", re.M),
}


def parse_probe_output(text: str) -> Hardware:
    """Extract ram_gb, gpu, vram_gb, os from pasted probe output. Partial is fine."""
    hw = Hardware()
    found = {name: pat.search(text) for name, pat in _PATTERNS.items()}
    is_windows = "TotalPhysicalMemory" in text or "AdapterRAM" in text

    if m := found["mac_mem"]:
        hw.ram_gb = float(m.group(1))
    elif m := found["memsize"]:
        hw.ram_gb = round(int(m.group(1)) / 2**30)
    elif m := found["free_g"]:
        hw.ram_gb = float(m.group(1)) + 1  # free -g truncates; 15 usually means 16
    elif m := found["win_mem"]:
        hw.ram_gb = round(int(m.group(1)) / 2**30)

    if m := found["mac_chip"]:
        hw.gpu = m.group(1).strip() + " (unified memory)"
        hw.os = "macos"
    elif m := found["nvidia_csv"]:
        hw.gpu = m.group(1).strip()
        hw.vram_gb = round(int(m.group(2)) / 1024, 1)
    elif is_windows and (m := found["win_gpu_line"]):
        hw.gpu = m.group(1).strip()
        hw.vram_gb = round(int(m.group(3)) / 2**30, 1)
    elif is_windows and (m := found["win_gpu_name"]):
        hw.gpu = m.group(1).strip()
    elif m := found["lspci_vga"]:
        hw.gpu = m.group(1).strip()

    if hw.os is None:
        if m := found["uname"]:
            hw.os = "macos" if m.group(1) == "Darwin" else "linux"
        elif is_windows:
            hw.os = "windows"
        elif found["free_g"]:
            hw.os = "linux"
    return hw


def looks_like_probe_output(text: str) -> bool:
    """Cheap check the router uses to spot pasted probe output."""
    markers = ("Chip:", "Memory:", "hw.memsize", "Mem:", "MiB", "TotalPhysicalMemory",
               "AdapterRAM", "VGA compatible")
    return any(m in text for m in markers)
