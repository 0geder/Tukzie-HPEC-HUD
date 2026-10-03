#!/usr/bin/env python3
"""SW-7 pre-test check (DashboardIntegration/TELEMETRY_LINK.md section 4.4).

Run before every test session, from the laptop or the Pi 5. Standard
library only. Prints one line per item, PASS / FAIL / WARN with the
measured value, and exits 0 only if every critical item passes:
telemetry answering and fresh, both IMU rates, camera /alerts answering.

  python sw7_check.py                       # find the Pi 4 by itself
  python sw7_check.py --pi4 10.20.0.1 --pi5 Pirate5.local
  python sw7_check.py --json                # machine-readable

Finding the Pi 4 (unless --pi4 is given), first that answers
GET /telemetry within 3 s: 127.0.0.1 (single-Pi setup), 10.20.0.1 (wired
sw7-link), the source of a UDP beacon on port 50808 (listens 3 s),
pi4-camera.local, then each --candidates address.

Checks over ssh (BatchMode, so a missing key fails quickly and is shown
as WARN): bridge and detector services, under-voltage flags, temperature
on the Pi 4; the dashboard process from ~/Dashboard_sw7 and its
TUKZIE_LIVE_ONLY setting on the Pi 5. When a Pi is this machine, the
same commands run locally instead.
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

TELEMETRY_PORT = 8081
CAMERA_PORT = 8080
BEACON_PORT = 50808
WIRED_PI4 = "10.20.0.1"
MDNS_PI4 = "pi4-camera.local"
DEFAULT_PI5 = "Pirate5.local"
ESP32_MAX_AGE_MS = 3000
IMU_MIN_HZ = 195.0
LOCAL_NAMES = ("127.0.0.1", "localhost", "::1")

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"


class Report:
    def __init__(self, quiet=False):
        self.items = []
        self.quiet = quiet

    def add(self, name, status, value, critical=False):
        self.items.append({"name": name, "status": status, "value": value, "critical": critical})
        if not self.quiet:
            tag = " (critical)" if critical else ""
            print("%-4s  %-28s %s%s" % (status, name, value, tag), flush=True)

    def ok(self):
        return all(i["status"] == PASS for i in self.items if i["critical"])


# HTTP -----------------------------------------------------------------------

def get_json(url, timeout=3.0):
    """(dict, elapsed_ms) or raises OSError/ValueError."""
    t0 = time.monotonic()
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = r.read()
    return json.loads(body.decode("utf-8")), (time.monotonic() - t0) * 1000


def probe_telemetry(host, port, timeout=3.0):
    """True if http://host:port/telemetry answers with the bridge's JSON."""
    try:
        d, _ = get_json("http://%s:%d/telemetry" % (host, port), timeout)
    except Exception:
        return False
    return isinstance(d, dict) and "bridge" in d


def listen_beacon(port=BEACON_PORT, wait_s=3.0):
    """Wait for one SW-7 beacon. Returns (source address, payload dict),
    or (None, reason) when none arrives or the port cannot be opened."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", port))
        except OSError as e:
            return None, "cannot listen on UDP %d (%s)" % (port, e)
        deadline = time.monotonic() + wait_s
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None, "no beacon in %.0f s" % wait_s
            s.settimeout(left)
            try:
                data, addr = s.recvfrom(2048)
            except socket.timeout:
                return None, "no beacon in %.0f s" % wait_s
            except OSError as e:
                return None, "beacon receive error (%s)" % e
            try:
                d = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("sw7") == "pi4":
                return addr[0], d
    finally:
        s.close()


def discover_pi4(args, probe=probe_telemetry, beacon=listen_beacon):
    """Returns (host, how, telemetry_port, camera_port, tried) or
    (None, None, ..., tried) if nothing answered."""
    tp, cp = args.telemetry_port, args.camera_port
    tried = []
    if args.pi4:
        tried.append(args.pi4)
        if probe(args.pi4, tp):
            return args.pi4, "given (--pi4)", tp, cp, tried
        return None, None, tp, cp, tried
    for host, how in (("127.0.0.1", "local (this machine)"), (WIRED_PI4, "wired (sw7-link)")):
        tried.append(host)
        if probe(host, tp):
            return host, how, tp, cp, tried
    src, info = beacon(args.beacon_port, args.beacon_wait)
    if src is None:
        tried.append("beacon: %s" % info)
    else:
        btp = int(info.get("telemetry_port") or tp)
        bcp = int(info.get("camera_port") or cp)
        tried.append("beacon from %s" % src)
        if probe(src, btp):
            return src, "beacon (host %s)" % info.get("host"), btp, bcp, tried
    hosts = [(MDNS_PI4, "mdns")] + [(c, "candidate") for c in args.candidates]
    for host, how in hosts:
        tried.append(host)
        if probe(host, tp):
            return host, how, tp, cp, tried
    return None, None, tp, cp, tried


# Command execution (ssh or local) ---------------------------------------------

def is_local(host):
    if host in LOCAL_NAMES:
        return True
    h = host.lower().split(".")[0]
    return h == socket.gethostname().lower().split(".")[0]


def run_remote(host, user, key, script, timeout=20):
    """Run a bash script on host (locally if host is this machine).
    Returns (ok, stdout or error text)."""
    if is_local(host) and sys.platform.startswith("linux"):
        cmd = ["bash", "-c", script]
    else:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
               "-o", "StrictHostKeyChecking=accept-new"]
        if key and os.path.exists(os.path.expanduser(key)):
            cmd += ["-i", os.path.expanduser(key)]
        cmd += ["%s@%s" % (user, host), script]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        return False, "cannot run %s (%s)" % (cmd[0], e)
    except subprocess.TimeoutExpired:
        return False, "timed out after %d s" % timeout
    if p.returncode == 255 and cmd[0] == "ssh":
        return False, (p.stderr.strip().splitlines() or ["ssh failed"])[-1]
    return True, p.stdout


def parse_kv(text):
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out.setdefault(k.strip(), v.strip())
    return out


PI4_SCRIPT = r"""
echo "bridge=$(systemctl is-active telemetry-bridge 2>/dev/null)"
echo "detector=$(systemctl is-active hazard-detector 2>/dev/null)"
echo "detector_pids=$(pgrep -f 'hazard_detector\.py' | tr '\n' ' ')"
echo "throttled=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)"
t=$(vcgencmd measure_temp 2>/dev/null | sed "s/temp=//; s/'C//")
[ -z "$t" ] && [ -r /sys/class/thermal/thermal_zone0/temp ] && t=$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
echo "temp=$t"
"""

PI5_SCRIPT = r"""
want="$HOME/Dashboard_sw7"
echo "host=$(hostname)"
for p in $(pgrep -u "$(id -u)" -f python); do
  [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$want" ] || continue
  echo "pid=$p"
  lo=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^TUKZIE_LIVE_ONLY=')
  if [ -n "$lo" ]; then echo "live_only=${lo#TUKZIE_LIVE_ONLY=}"; else echo "live_only=<unset>"; fi
done
[ -r "$want/DEPLOYED_COMMIT" ] && echo "commit=$(head -c 40 "$want/DEPLOYED_COMMIT")"
"""

THROTTLE_BITS = {0: "under-voltage now", 1: "frequency capped now", 2: "throttled now",
                 3: "soft temperature limit now", 16: "under-voltage since boot",
                 17: "frequency capped since boot", 18: "throttled since boot",
                 19: "soft temperature limit since boot"}


def decode_throttled(text):
    """Returns (status, description) for a vcgencmd get_throttled value."""
    try:
        v = int(text, 16)
    except (TypeError, ValueError):
        return WARN, "not available (%r)" % text
    flags = [name for bit, name in sorted(THROTTLE_BITS.items()) if v & (1 << bit)]
    if not flags:
        return PASS, "0x%x, no under-voltage or throttling since boot" % v
    status = FAIL if v & 0x1 else WARN
    return status, "0x%x: %s" % (v, ", ".join(flags))


# Checks ---------------------------------------------------------------------

def check_telemetry(rep, d, ms):
    rep.add("telemetry /telemetry", PASS, "answered in %.0f ms" % ms, critical=True)
    e = d.get("esp32")
    if not isinstance(e, dict):
        rep.add("esp32 data fresh", FAIL, "esp32 is null (no DASH line, or serial port lost)", critical=True)
        rep.add("IMU rates", FAIL, "no esp32 data", critical=True)
        return None
    age = e.get("age_ms")
    if isinstance(age, (int, float)) and age < ESP32_MAX_AGE_MS:
        rep.add("esp32 data fresh", PASS, "age %d ms" % age, critical=True)
    else:
        rep.add("esp32 data fresh", FAIL, "age %s ms (limit %d)" % (age, ESP32_MAX_AGE_MS), critical=True)
    hz = e.get("imu_hz")
    if isinstance(hz, list) and len(hz) == 2 and all(isinstance(x, (int, float)) for x in hz):
        st = PASS if min(hz) >= IMU_MIN_HZ else FAIL
        rep.add("IMU rates", st, "IMU1 %.1f Hz, IMU2 %.1f Hz (min %.0f)" % (hz[0], hz[1], IMU_MIN_HZ),
                critical=True)
    else:
        rep.add("IMU rates", FAIL, "imu_hz missing or invalid: %r" % (hz,), critical=True)
    fw = e.get("fw")
    rep.add("esp32 firmware", PASS if isinstance(fw, str) and fw else WARN, repr(fw) if fw else "missing")
    return e.get("drops")


def check_tof(rep, d):
    t = d.get("tof")
    if not isinstance(t, dict):
        rep.add("ToF sensors", WARN, "tof is null (sensors absent or not read)")
        return
    vals = {k: t.get("%s_mm" % k) for k in ("left", "ahead", "right")}
    text = ", ".join("%s %s" % (k, "null" if v is None else "%d mm" % v) for k, v in vals.items())
    rep.add("ToF sensors", PASS if all(v is not None for v in vals.values()) else WARN, text)


def check_drops(rep, first, second, window_s):
    if not (isinstance(first, list) and isinstance(second, list) and len(first) == len(second) == 2):
        rep.add("IMU drops", WARN, "drops not available (%r, %r)" % (first, second))
        return
    delta = [b - a for a, b in zip(first, second)]
    if delta == [0, 0]:
        rep.add("IMU drops", PASS, "unchanged over %.1f s (total %s)" % (window_s, second))
    else:
        rep.add("IMU drops", WARN, "+%d / +%d over %.1f s (total %s)" % (delta[0], delta[1], window_s, second))


def check_camera(rep, host, port):
    try:
        d, ms = get_json("http://%s:%d/alerts" % (host, port), timeout=2.0)
        fps = d.get("fps")
    except Exception as e:
        rep.add("camera /alerts", FAIL, "no answer from %s:%d (%s)" % (host, port, e), critical=True)
        return
    if not isinstance(fps, (int, float)):
        rep.add("camera /alerts", FAIL, "answered but no fps field", critical=True)
        return
    rep.add("camera /alerts", PASS, "%.1f fps, %d active alert(s), %.0f ms" % (
        fps, len(d.get("active") or []), ms), critical=True)
    if fps <= 0:
        rep.add("camera frames", WARN, "fps is 0: detector answering but no frames processed yet")


def check_pi4_ssh(rep, host, args):
    ok, out = run_remote(host, args.pi4_user, args.ssh_key, PI4_SCRIPT)
    if not ok:
        rep.add("Pi 4 ssh", WARN, "skipped Pi 4 service checks: %s" % out)
        return
    kv = parse_kv(out)
    b = kv.get("bridge") or "unknown"
    rep.add("telemetry-bridge service", PASS if b == "active" else FAIL, b)
    det = kv.get("detector") or "unknown"
    pids = kv.get("detector_pids", "").split()
    if det == "active":
        rep.add("hazard-detector service", PASS, "active")
    elif pids:
        rep.add("hazard-detector service", WARN, "%s, but detector running by hand (pid %s)" % (det, pids[0]))
    else:
        rep.add("hazard-detector service", FAIL, "%s, no detector process" % det)
    st, desc = decode_throttled(kv.get("throttled"))
    rep.add("Pi 4 power (throttled)", st, desc)
    try:
        t = float(kv.get("temp"))
        rep.add("Pi 4 temperature", PASS if t < 70 else (WARN if t < 80 else FAIL), "%.1f C" % t)
    except (TypeError, ValueError):
        rep.add("Pi 4 temperature", WARN, "not available")


RPI_MAC_PREFIXES = ("2c:cf:67", "d8:3a:dd", "dc:a6:32", "e4:5f:01", "b8:27:eb", "28:cd:c1")
LAST_PI5_FILE = os.path.expanduser("~/.sw7_last_pi5_host")


def neighbour_rpis():
    """IPv4 addresses of Raspberry Pis in this machine's neighbour (ARP) table."""
    try:
        cmd = ["arp", "-a"] if os.name == "nt" else ["ip", "neigh"]
        text = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for line in text.splitlines():
        low = line.lower().replace("-", ":")
        ip = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", low)
        if ip and any(pref in low for pref in RPI_MAC_PREFIXES):
            out.append(ip.group(1))
    return list(dict.fromkeys(out))


def sweep_local_subnets():
    """Ping every address of this machine's /24 networks briefly, so the ARP table fills."""
    nets = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            a = info[4][0]
            if not a.startswith("127."):
                nets.add(a.rsplit(".", 1)[0])
    except OSError:
        pass
    flag, wait = (["-n", "1", "-w", "1500"] if os.name == "nt" else ["-c", "1", "-W", "2"]), []
    for net in nets:
        for i in range(1, 255):
            try:
                wait.append(subprocess.Popen(["ping", *flag, "%s.%d" % (net, i)],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            except OSError:
                break
    for p in wait:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def ssh_hosts_on_local_subnets(port=22, timeout=1.5):
    """Addresses on this machine's /24 networks that accept a TCP connection on the ssh port."""
    import concurrent.futures
    nets, own = set(), set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            a = info[4][0]
            if not a.startswith("127."):
                nets.add(a.rsplit(".", 1)[0]); own.add(a)
    except OSError:
        return []

    def is_open(ip):
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
            return ip
        except OSError:
            return None
        finally:
            s.close()

    ips = ["%s.%d" % (n, i) for n in nets for i in range(1, 255) if "%s.%d" % (n, i) not in own]
    with concurrent.futures.ThreadPoolExecutor(64) as ex:
        return [ip for ip in ex.map(is_open, ips) if ip]


def find_pi5(args, name="pirate5"):
    """Find the dashboard Pi when its .local name does not resolve (phone hotspots often
    block mDNS): the last address that worked, then every Raspberry Pi on the local
    network, identified by asking its hostname over ssh."""
    candidates = []
    try:
        candidates.append(open(LAST_PI5_FILE).read().strip())
    except OSError:
        pass
    candidates += neighbour_rpis()
    if not candidates[1:]:
        # Phone hotspots often drop pings between clients (3 Oct), so look for open ssh ports.
        candidates += ssh_hosts_on_local_subnets()
    for host in dict.fromkeys(c for c in candidates if c):
        ok, out = run_remote(host, args.pi5_user, args.ssh_key, "hostname", timeout=8)
        if ok and out.strip().lower() == name:
            return host
    return None


def check_pi5(rep, args):
    host = args.pi5
    if host == "auto":
        host = "localhost" if (sys.platform.startswith("linux")
                               and os.path.isdir(os.path.expanduser("~/Dashboard_sw7"))) else DEFAULT_PI5
    ok, out = run_remote(host, args.pi5_user, args.ssh_key, PI5_SCRIPT)
    if not ok and args.pi5 == "auto" and host == DEFAULT_PI5:
        found = find_pi5(args)
        if found:
            host = found
            ok, out = run_remote(host, args.pi5_user, args.ssh_key, PI5_SCRIPT)
    if ok and host not in ("localhost", DEFAULT_PI5):
        try:
            with open(LAST_PI5_FILE, "w") as f:
                f.write(host)
        except OSError:
            pass
    if not ok:
        rep.add("Pi 5 reachable", WARN, "%s: %s" % (host, out))
        return
    kv = parse_kv(out)
    rep.add("Pi 5 reachable", PASS, "%s (hostname %s)" % (host, kv.get("host", "?")))
    if "pid" not in kv:
        rep.add("SW-7 dashboard running", FAIL, "no python process with cwd ~/Dashboard_sw7")
        return
    commit = kv.get("commit")
    rep.add("SW-7 dashboard running", PASS, "pid %s%s" % (kv["pid"], ", commit %s" % commit[:10] if commit else ""))
    lo = kv.get("live_only", "<unset>")
    rep.add("TUKZIE_LIVE_ONLY", PASS if lo not in ("<unset>", "", "0") else WARN, lo)


def run(args):
    rep = Report(quiet=args.json)
    host, how, tp, cp, tried = discover_pi4(args)
    result = {"pi4": host, "found_by": how, "tried": tried}
    if host is None:
        rep.add("Pi 4 found", FAIL, "nothing answered on :%d (tried %s)" % (tp, ", ".join(tried)), critical=True)
    else:
        rep.add("Pi 4 found", PASS, "%s via %s" % (host, how))
        t0 = time.monotonic()
        first = None
        try:
            d, ms = get_json("http://%s:%d/telemetry" % (host, tp), timeout=2.0)
        except Exception as e:
            rep.add("telemetry /telemetry", FAIL, "no answer (%s)" % e, critical=True)
            d = None
        if d is not None:
            first = check_telemetry(rep, d, ms)
            check_tof(rep, d)
        check_camera(rep, host, cp)
        if args.no_ssh:
            rep.add("Pi 4 ssh", WARN, "skipped (--no-ssh)")
        else:
            check_pi4_ssh(rep, host, args)
        if d is not None and first is not None:
            left = args.drops_window - (time.monotonic() - t0)
            if left > 0:
                time.sleep(left)
            try:
                d2, _ = get_json("http://%s:%d/telemetry" % (host, tp), timeout=2.0)
                second = (d2.get("esp32") or {}).get("drops")
            except Exception:
                second = None
            check_drops(rep, first, second, time.monotonic() - t0)
    if args.no_ssh or args.pi5 == "none":
        rep.add("Pi 5 reachable", WARN, "skipped")
    else:
        check_pi5(rep, args)
    ok = rep.ok()
    result.update(ok=ok, checks=rep.items)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        crit_fail = [i["name"] for i in rep.items if i["critical"] and i["status"] != PASS]
        print("\nRESULT: %s" % ("READY (all critical items pass)" if ok else
                                "NOT READY, critical: %s" % ", ".join(crit_fail)))
    return 0 if ok else 1


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="SW-7 pre-test check (TELEMETRY_LINK.md 4.4)")
    ap.add_argument("--pi4", default=None, metavar="HOST", help="Pi 4 address (default: discover)")
    ap.add_argument("--pi5", default="auto", metavar="HOST",
                    help="Pi 5 address; 'auto' = this machine if it has ~/Dashboard_sw7, else %s; "
                         "'none' = skip" % DEFAULT_PI5)
    ap.add_argument("--candidates", nargs="*", default=[], metavar="HOST",
                    help="Extra Pi 4 addresses to try last")
    ap.add_argument("--ssh-key", default="~/.ssh/pi4_camera_key")
    ap.add_argument("--pi4-user", default="ogeder")
    ap.add_argument("--pi5-user", default="piadam")
    ap.add_argument("--no-ssh", action="store_true", help="Skip every ssh check (shown as WARN)")
    ap.add_argument("--json", action="store_true", help="Machine-readable output only")
    ap.add_argument("--telemetry-port", type=int, default=TELEMETRY_PORT)
    ap.add_argument("--camera-port", type=int, default=CAMERA_PORT)
    ap.add_argument("--beacon-port", type=int, default=BEACON_PORT)
    ap.add_argument("--beacon-wait", type=float, default=3.0, help="Seconds to listen for the beacon")
    ap.add_argument("--drops-window", type=float, default=5.0, help="Seconds between the two drops readings")
    return ap.parse_args(argv)


if __name__ == "__main__":
    sys.exit(run(parse_args()))
