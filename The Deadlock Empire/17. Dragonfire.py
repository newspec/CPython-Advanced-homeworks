# Dragonfire - The Deadlock Empire Challenge

import threading

# ---------- shared state ----------
firebreathing_lock = threading.Lock()
fireball = threading.Semaphore(0)   # SemaphoreSlim fireball [counter: 0]
c = 0

# ---------- bug detection ----------
in_critical = 0
in_critical_lock = threading.Lock()
critical_violation = threading.Event()

# ---------- synchronisation to force the exact interleaving ----------
# Phase 1: Firebreathing Head signals it has done c = c - 1 and is waiting
after_decrement  = threading.Event()
# Phase 2: Recharging Head signals it has done 3× release+increment
after_3_releases = threading.Event()
# Phase 3: both threads rendezvous *inside* critical_section
both_inside = threading.Barrier(2)

# ---------- helpers ----------
def incinerate_enemies(): pass
def blast_enemies():      pass

def critical_section(name: str):
    global in_critical
    print(f"  [{name}] entering critical_section")

    # Both threads increment in_critical before either checks the value
    with in_critical_lock:
        in_critical += 1

    # Barrier: hold here until BOTH threads have incremented
    try:
        both_inside.wait(timeout=2)
    except threading.BrokenBarrierError:
        pass

    # Now both threads read in_critical — it must be 2
    count = in_critical
    if count >= 2:
        print(f"  [BUG] {count} threads in critical_section simultaneously!")
        critical_violation.set()

    with in_critical_lock:
        in_critical -= 1

    print(f"  [{name}] leaving critical_section")

# ---------- Firebreathing Head ----------
def firebreathing_head():
    """
    while (true) {
      Monitor.Enter(firebreathing);
      incinerate_enemies();
      if (fireball.Wait(500)) {
        blast_enemies();
        if (fireball.Wait(500)) {
          if (fireball.Wait(500)) {
            critical_section();
          }
        }
      }
      c = c - 1;   // <-- preemption point
      c = c + 1;
      Monitor.Exit(firebreathing);
    }
    """
    global c
    with firebreathing_lock:
        incinerate_enemies()

        # FORCED INTERLEAVING:
        # Do c = c - 1 first, then pause so Recharging Head can run 3 loops
        c = c - 1                   # c: 0 -> -1
        print(f"  [FirebreathingHead] c = c - 1  ->  c = {c}")
        after_decrement.set()       # signal Recharging Head to proceed
        after_3_releases.wait()     # wait until fireball = 3, c = 2

        print(f"  [FirebreathingHead] resumed: c = {c}, fireball = 3")

        # fireball counter is now 3 -> all three acquires succeed immediately
        if fireball.acquire(timeout=1):         # 3 -> 2
            blast_enemies()
            if fireball.acquire(timeout=1):     # 2 -> 1
                if fireball.acquire(timeout=1): # 1 -> 0
                    critical_section("FirebreathingHead")

        c = c + 1
    # Monitor.Exit

# ---------- Recharging Head ----------
def recharging_head():
    """
    while (true) {
      if (c < 2) {
        fireball.Release();
        c++;
      } else {
        critical_section();
      }
    }
    """
    global c

    # Wait until Firebreathing Head has decremented c to -1
    after_decrement.wait()
    print(f"  [RechargingHead] starting 3 release+increment loops, c = {c}")

    # 3 iterations: c is -1, 0, 1 -> all < 2
    for i in range(3):
        assert c < 2, f"Expected c < 2 but c = {c}"
        fireball.release()   # fireball: 0->1, 1->2, 2->3
        c += 1               # c: -1->0, 0->1, 1->2
        print(f"  [RechargingHead] loop {i+1}: fireball.release(); c++ -> c = {c}")

    after_3_releases.set()   # tell Firebreathing Head to resume
    print(f"  [RechargingHead] done looping: c = {c}, entering else branch")

    # c == 2 -> else branch -> critical_section
    critical_section("RechargingHead")

# ---------- main ----------
if __name__ == "__main__":
    print("Dragonfire – forced race-condition demo")
    print("=" * 50)
    print(f"Initial state: c = {c}, fireball counter = 0\n")

    t1 = threading.Thread(target=firebreathing_head, name="FirebreathingHead")
    t2 = threading.Thread(target=recharging_head,    name="RechargingHead")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print()
    if critical_violation.is_set():
        print("[RESULT] Bug reproduced successfully!")
    else:
        print("[RESULT] Bug was NOT triggered.")
