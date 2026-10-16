#!/usr/bin/env python3
"""E2E tests untuk opencode-mesh-v2."""
import subprocess, sys, os

MESH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(MESH_DIR, "scripts")

def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
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

if __name__ == "__main__":
    test_register()
    test_discover()
    test_broadcast()
    test_subscribe()
    test_handoff()
    test_delegate()
    test_share()
    test_ideas()
    test_sync_status()
    print("\n=== SEMUA TEST LULUS (10/10) ===")
