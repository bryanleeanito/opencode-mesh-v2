#!/usr/bin/env python3
"""E2E tests untuk opencode-mesh-v2."""
import subprocess, sys, os

MESH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(MESH_DIR, "scripts")
_RUN_DIR = None

def _run_dir():
    # Clone temp scripts+state sekali per run: tes E2E menulis ke salinan,
    # bukan ke bus asli (registry/broadcast asli tidak boleh ikut ter-push).
    global _RUN_DIR
    if _RUN_DIR is None:
        import shutil, tempfile
        base = os.path.join(tempfile.gettempdir(), "opencode")
        if not os.path.isdir(base):
            os.makedirs(base, exist_ok=True)
        d = tempfile.mkdtemp(prefix="mesh-run-", dir=base)
        shutil.copytree(os.path.join(MESH_DIR, "scripts"),
                        os.path.join(d, "scripts"))
        shutil.copytree(os.path.join(MESH_DIR, "state"),
                        os.path.join(d, "state"))
        _RUN_DIR = d
    return _RUN_DIR

def run(script, *args):
    r = subprocess.run([sys.executable,
                        os.path.join(_run_dir(), "scripts", script), *args],
                       capture_output=True, text=True, timeout=10)
    return r.returncode, r.stdout, r.stderr

def test_register():
    rc, out, _ = run("register.py", "--name", "test-machine", "--role", "test", "--ip", "127.0.0.1")
    assert rc == 0
    assert "Registered" in out
    print("[PASS] register")

def test_discover():
    rc, out, _ = run("discover.py", "--all")
    assert rc == 0
    assert "machines" in out.lower() or "Online" in out
    print("[PASS] discover")

def test_broadcast():
    rc, out, _ = run("broadcast.py", "--message", "test broadcast")
    assert rc == 0
    assert "Broadcast" in out
    print("[PASS] broadcast")

def test_subscribe():
    rc, out, _ = run("subscribe.py", "--topic", "test")
    assert rc == 0
    assert "Subscribed" in out
    print("[PASS] subscribe")

def test_handoff():
    rc, out, _ = run("handoff.py", "--to", "test-machine", "--task", "test task")
    assert rc == 0
    assert "Handoff" in out
    print("[PASS] handoff")

def test_delegate():
    rc, out, _ = run("delegate.py", "--to", "test-machine", "--task", "test task")
    assert rc == 0
    assert "Task" in out
    print("[PASS] delegate")

def test_share():
    rc, out, _ = run("share.py", "--type", "finding", "--message", "test finding")
    assert rc == 0
    assert "FINDING" in out
    print("[PASS] share")

def test_ideas():
    rc, out, _ = run("ideas.py", "--add", "test idea")
    assert rc == 0
    assert "Idea" in out
    print("[PASS] ideas")

def test_sync_status():
    rc, out, _ = run("sync.py", "--status")
    assert rc == 0
    assert "sync status" in out.lower() or "entries" in out
    print("[PASS] sync status")

def test_mesh_integrator_list():
    rc, out, _ = run("mesh_integrator.py", "list-kits")
    assert rc == 0
    assert "Available kits" in out
    assert "waf-bypass" in out
    print("[PASS] mesh_integrator list")

# --- mesh_status.py (offline, state terisolasi di temp) ---

def run_env(script, env_extra, *args):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True, timeout=10, env=env)
    return r.returncode, r.stdout, r.stderr

def _mesh_temp_state(registry=True):
    import json, tempfile
    base = os.path.join(tempfile.gettempdir(), "opencode")
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
    d = tempfile.mkdtemp(prefix="mesh-status-", dir=base)
    if registry:
        data = {"machines": [{"name": "uji", "role": "test", "ip": "127.0.0.1",
                              "capabilities": [], "hostname": "uji-host",
                              "last_seen": "2026-01-01T00:00:00",
                              "status": "online"}]}
        with open(os.path.join(d, "registry.json"), "w") as f:
            json.dump(data, f)
    return d

def _mesh_env(d):
    return {"MESH_STATE_DIR": d,
            "MESH_SELF_FILE": os.path.join(d, ".self.json")}

def _mesh_mod():
    import importlib.util
    path = os.path.join(SCRIPTS, "mesh_status.py")
    spec = importlib.util.spec_from_file_location("mesh_status_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_mesh_status_set_name():
    import shutil
    d = _mesh_temp_state()
    try:
        rc, out, err = run_env("mesh_status.py", _mesh_env(d),
                               "--name", "uji", "--local")
        assert rc == 0, "rc=%d out=%s err=%s" % (rc, out, err)
        assert os.path.exists(os.path.join(d, ".self.json"))
        pres = os.path.join(d, "presence", "uji.json")
        assert os.path.exists(pres)
        import json
        with open(pres) as f:
            data = json.load(f)
        assert isinstance(data["last_seen"], int)
        assert data["status"] == "online"
        print("[PASS] mesh status set-name")
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_mesh_status_unknown_name():
    import shutil
    d = _mesh_temp_state()
    try:
        rc, out, err = run_env("mesh_status.py", _mesh_env(d),
                               "--name", "ngaco", "--local")
        assert rc == 1, "rc=%d" % rc
        assert "belum terdaftar" in out
        print("[PASS] mesh status unknown-name")
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_mesh_status_missing_self():
    import shutil
    d = _mesh_temp_state()
    try:
        rc, out, err = run_env("mesh_status.py", _mesh_env(d), "--local")
        assert rc == 1, "rc=%d" % rc
        assert "belum set nama" in out
        print("[PASS] mesh status missing-self")
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_mesh_status_tabel():
    import shutil
    d = _mesh_temp_state()
    try:
        rc, _, _ = run_env("mesh_status.py", _mesh_env(d),
                           "--name", "uji", "--local")
        assert rc == 0
        rc, out, err = run_env("mesh_status.py", _mesh_env(d), "--local")
        assert rc == 0, "rc=%d out=%s err=%s" % (rc, out, err)
        assert "uji" in out
        assert "baru saja" in out or "mnt lalu" in out
        print("[PASS] mesh status tabel")
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_mesh_status_rate_limit():
    mod = _mesh_mod()
    assert mod.boleh_push_cron(1000, 1300) is False  # 300s < 600s
    assert mod.boleh_push_cron(1000, 1700) is True   # 700s >= 600s
    assert mod.boleh_push_cron(None, 1000) is True   # belum pernah ada
    print("[PASS] mesh status rate-limit")

def test_mesh_status_umur():
    mod = _mesh_mod()
    assert mod.umur_str(1000, 1030) == "baru saja"   # < 60s
    assert mod.umur_str(1000, 1300) == "5 mnt lalu"  # 300s
    assert mod.umur_str(1000, 8200) == "2 jam lalu"  # 7200s
    assert mod.umur_str(1000, 900) == "baru saja"    # negatif di-clamp
    print("[PASS] mesh status umur")

if __name__ == "__main__":
    import shutil
    try:
        test_register()
        test_discover()
        test_broadcast()
        test_subscribe()
        test_handoff()
        test_delegate()
        test_share()
        test_ideas()
        test_sync_status()
        test_mesh_integrator_list()
        test_mesh_status_set_name()
        test_mesh_status_unknown_name()
        test_mesh_status_missing_self()
        test_mesh_status_tabel()
        test_mesh_status_rate_limit()
        test_mesh_status_umur()
        print("\n=== SEMUA TEST LULUS (16/16) ===")
    finally:
        if _RUN_DIR:
            shutil.rmtree(_RUN_DIR, ignore_errors=True)
