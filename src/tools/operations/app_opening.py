import os
import shutil
from pathlib import Path
import subprocess
import sys
import json
import time
import webbrowser
from difflib import SequenceMatcher
import re

# ---------- Config ----------
CACHE_FILE = "app_index.json"
ALIASES_FILE = "aliases.json"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours
TOP_N = 6
AUTO_LAUNCH_THRESHOLD = 0.92  # auto-launch if >=
MIN_DISPLAY_SCORE = 0.30

DEFAULT_ALIASES = {
    "calculator": r"C:\Windows\System32\calc.exe",
    "notepad": r"C:\Windows\System32\notepad.exe"
}

# ---------- Utilities ----------
def read_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write_json(p, data):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def is_windows():
    return os.name == "nt"

# ---------- Indexing ----------
def index_start_and_desktop_shortcuts():
    """Collect .lnk/.url/.appref-ms from Start Menu (all users + current) and Desktop."""
    roots = [
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expanduser(r"~\Desktop"),
        os.path.expandvars(r"%PUBLIC%\Desktop"),
    ]
    apps = []
    seen = set()
    for root in roots:
        if not root or not os.path.exists(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith((".lnk", ".url", ".appref-ms")):
                    full = os.path.join(dirpath, fn)
                    display = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").strip()
                    key = ("start", display.lower(), os.path.dirname(full).lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    apps.append({"name": display, "path": full, "type": "StartShortcut"})
    return apps

def index_path_executables():
    apps = []
    seen = set()
    path_env = os.environ.get("PATH", "")
    for d in path_env.split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        try:
            for fn in os.listdir(d):
                if not fn.lower().endswith(".exe"):
                    continue
                full = os.path.join(d, fn)
                name = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").title()

                key = ("path", name.lower(), os.path.dirname(full).lower())
                if key in seen:
                    continue
                seen.add(key)
                apps.append({"name": name, "path": full, "type": "PathExe"})
        except Exception:
            continue
    return apps

def index_registry_installed():
    apps = []
    try:
        import winreg
    except Exception:
        return apps
    uninstall_paths = [
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    seen = set()
    for hive in hives:
        for path in uninstall_paths:
            try:
                key = winreg.OpenKey(hive, path)
            except Exception:
                continue
            try:
                count = winreg.QueryInfoKey(key)[0]
            except Exception:
                count = 0
            for i in range(count):
                try:
                    sub = winreg.EnumKey(key, i)
                    subk = winreg.OpenKey(key, sub)
                except Exception:
                    continue
                try:
                    dn = winreg.QueryValueEx(subk, "DisplayName")[0]
                    if not dn:
                        winreg.CloseKey(subk); continue
                    dn = str(dn).strip()
                    if dn.lower() in seen:
                        winreg.CloseKey(subk); continue
                except Exception:
                    winreg.CloseKey(subk); continue

                launch = ""
                try:
                    di = winreg.QueryValueEx(subk, "DisplayIcon")[0]
                    if di:
                        di = str(di)
                        launch = di.split(",")[0].strip().strip('"')
                except Exception:
                    pass
                try:
                    il = winreg.QueryValueEx(subk, "InstallLocation")[0]
                    if il and os.path.isdir(il):
                        for f in os.listdir(il):
                            if f.lower().endswith(".exe") and not any(x in f.lower() for x in ("unins","setup","update","install")):
                                launch = os.path.join(il, f); break
                except Exception:
                    pass

                launch = os.path.expandvars(str(launch or ""))
                if launch and os.path.exists(launch) and "unins" not in launch.lower():
                    apps.append({"name": dn, "path": launch, "type": "Traditional"})
                    seen.add(dn.lower())
                winreg.CloseKey(subk)
    return apps

def index_uwp_apps():
    apps = []
    cmd = 'powershell -NoProfile -Command "Get-AppxPackage | Select-Object Name, PackageFamilyName, InstallLocation | ConvertTo-Json -Depth 3"'
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if res.returncode != 0 or not res.stdout:
            return apps
        data = json.loads(res.stdout)
        if isinstance(data, dict):
            data = [data]
        seen = set()
        for app in data:
            name = app.get("Name") or ""
            pf = app.get("PackageFamilyName") or ""
            il = app.get("InstallLocation") or ""
            human = normalize_uwp(name, raw_name=name, package_family=pf, install_location=il)
            key = ("uwp", human.lower())
            if key in seen:
                continue
            seen.add(key)
            launch_cmd = f"explorer.exe shell:appsFolder\\{pf}!App" if pf else None
            apps.append({"name": human, "path": il or pf, "launch_command": launch_cmd, "type": "UWP"})
    except Exception:
        pass
    return apps

def normalize_uwp(name, raw_name=None, package_family=None, install_location=None):
    name = (name or "").strip()
    raw = (raw_name or "").strip()
    pf = (package_family or "").strip()
    if '.' in name:
        after = name.split('.', 1)[1]
        if re.search('[A-Za-z]', after):
            name = after
    compact = re.sub(r'[^0-9A-Fa-f]', '', name)
    if len(compact) >= 8 and len(re.sub(r'[^A-Za-z]', '', name)) < 2:
        for src in (raw, pf):
            if src:
                toks = re.split(r'[^A-Za-z]+', src)
                toks = [t for t in toks if len(t) > 1 and re.search('[A-Za-z]', t)]
                if toks:
                    name = toks[-1]; break
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    name = re.sub(r'[_\.-]+', ' ', name).strip()
    return name or (raw or pf or "")

def build_index(force=False):
    cache = Path(CACHE_FILE)
    if cache.exists() and not force:
        try:
            data = read_json(CACHE_FILE)
            if data and "built_at" in data:
                if time.time() - data["built_at"] < CACHE_TTL_SECONDS:
                    return data["apps"]
        except Exception:
            pass
    print("Indexing apps... (this may take a few seconds)")
    apps = []
    apps.extend(index_start_and_desktop_shortcuts())
    apps.extend(index_path_executables())
    apps.extend(index_registry_installed())
    apps.extend(index_uwp_apps())
    # dedupe by (name,path)
    seen = set()
    uniq = []
    for a in apps:
        key = (a.get("name","").strip().lower(), str(a.get("path","")).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    out = {"built_at": time.time(), "apps": uniq}
    write_json(CACHE_FILE, out)
    return uniq

# ---------- Matching ----------
def normalize_query(q):
    q = (q or "").strip()
    q = re.sub(r'^(ms|microsoft|office)\s+', '', q, flags=re.I)
    return q

def similarity(search, candidate_name, candidate_path=None):
    if not search or not candidate_name:
        return 0.0
    s = search.lower().strip()
    t = candidate_name.lower().strip()
    if s == t:
        return 1.0
    if t.startswith(s):
        return 0.98
    if f" {s}" in t or f"-{s}" in t:
        return 0.92
    if s in t:
        return 0.86
    if candidate_path:
        base = os.path.splitext(os.path.basename(candidate_path))[0].lower()
        if s == base:
            return 0.995
        if base.startswith(s):
            return 0.96
        if s in base:
            return 0.90
    # token overlap
    s_tokens = re.split(r'[\s\-_]+', s)
    t_tokens = re.split(r'[\s\-_]+', t)
    overlap = sum(1 for tok in s_tokens if any(tok in tt for tt in t_tokens))
    if overlap:
        ratio = SequenceMatcher(None, s, t).ratio()
        return min(1.0, 0.55 + 0.45 * ratio + 0.1 * (overlap/len(s_tokens)))
    return SequenceMatcher(None, s, t).ratio() * 0.9

def find_matches(apps, query, topn=TOP_N, min_score=MIN_DISPLAY_SCORE):
    q = normalize_query(query)
    scored = []
    for a in apps:
        score = similarity(q, a.get("name",""), candidate_path=a.get("path",""))
        if score >= min_score:
            scored.append((a, score))
    def k(item):
        app, sc = item
        pr = {"Traditional": 3, "UWP": 3, "StartShortcut": 3, "PathExe": 1}
        return (sc, pr.get(app.get("type"), 1))
    scored.sort(key=k, reverse=True)
    # dedupe by name keep highest
    out = []
    seen = set()
    for app, sc in scored:
        nl = app.get("name","").strip().lower()
        if nl in seen:
            continue
        seen.add(nl)
        out.append((app, sc))
        if len(out) >= topn:
            break
    return out

# ---------- Launch ----------
def launch_entry(entry):
    typ = entry.get("type")
    try:
        if typ == "UWP":
            cmd = entry.get("launch_command")
            if not cmd:
                return False
            subprocess.Popen(cmd, shell=True)
            return True
        if typ == "StartShortcut":
            p = entry.get("path")
            if p and os.path.exists(p):
                os.startfile(p)
                return True
            return False
        # traditional or path exe or alias
        p = entry.get("path")
        if not p:
            return False
        # attempt direct subprocess launch (no shell) to avoid capturing terminal
        try:
            subprocess.Popen([p], shell=False)
            return True
        except Exception:
            # Some apps require shell, try via os.startfile as fallback
            try:
                os.startfile(p)
                return True
            except Exception:
                return False
    except Exception:
        return False

# ---------- Main Functions ----------
def load_aliases():
    a = read_json(ALIASES_FILE)
    if isinstance(a, dict):
        return {k.lower(): v for k, v in a.items()}
    try:
        write_json(ALIASES_FILE, DEFAULT_ALIASES)
    except Exception:
        pass
    return {k.lower(): v for k, v in DEFAULT_ALIASES.items()}

def open_web(query):
    q = query.strip()
    if not q:
        return
    webbrowser.open(f"https://www.bing.com/search?q={q.replace(' ','+')}")

def open_app(app_name):
    """
    Open an application by name.
    
    Args:
        app_name (str): Name of the application to open
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_windows():
        return (False, "This operation only runs on Windows.")

    if not app_name or not app_name.strip():
        return (False, "No app name provided")
    
    query = app_name.strip()
    
    # Build app index
    apps = build_index(force=False)
    aliases = load_aliases()
    
    # Check aliases first
    ak = query.lower()
    if ak in aliases:
        target = aliases[ak]
        ent = {"name": ak, "path": target, "type": "Alias"}
        if launch_entry(ent):
            return (True, f"Successfully launched {ak} via alias")
        else:
            return (False, f"Failed to launch alias {ak}")
    
    # Find matches
    matches = find_matches(apps, query, topn=TOP_N)
    if not matches:
        # No local match found, open web search as fallback
        open_web(query)
        return (True, f"No local app found for '{query}', opened web search")
    
    # Get the best match
    top_app, top_score = matches[0]
    
    # Auto-launch if score is high enough
    if top_score >= AUTO_LAUNCH_THRESHOLD:
        if launch_entry(top_app):
            return (True, f"Successfully launched {top_app.get('name')} (score {top_score:.2f})")
        else:
            open_web(query)
            return (False, f"Failed to launch {top_app.get('name')}, opened web search instead")
    else:
        # Launch the best match even if score is not high enough for auto-launch
        if launch_entry(top_app):
            return (True, f"Successfully launched {top_app.get('name')} (score {top_score:.2f})")
        else:
            open_web(query)
            return (False, f"Failed to launch {top_app.get('name')}, opened web search instead")
    return (False, "Unexpected error occurred while trying to open app {app_name}")