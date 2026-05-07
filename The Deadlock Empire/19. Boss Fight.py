# Boss Fight
import threading

# ── shared state ──────────────────────────────────────────────────────────────
darkness = 0
evil = 0
fortress = threading.Semaphore(0)   # SemaphoreSlim fortress [counter: 0]
sanctum = threading.Condition(threading.Lock())  # object sanctum (monitor)

# ── bug detection ─────────────────────────────────────────────────────────────
in_critical = 0
in_critical_lock = threading.Lock()
critical_violation = threading.Event()
both_inside = threading.Barrier(2)   # rendezvous inside critical_section

# ── synchronisation events to force the exact interleaving ───────────────────
# Phase 1: Thread 1 has completed 2 full loops (fortress counter == 2)
_fortress_charged = threading.Event()
# Phase 2: both threads have read darkness == 0 (race on darkness++)
_t0_read_darkness = threading.Event()
_t1_read_darkness = threading.Event()
# Phase 3: Thread 0 is blocked inside Monitor.Wait(sanctum)
_t0_waiting = threading.Event()

# ── helpers ───────────────────────────────────────────────────────────────────
def critical_section(name: str) -> None:
    global in_critical
    print(f"  [{name}] >>> entering critical_section")

    with in_critical_lock:
        in_critical += 1

    # Hold here until BOTH threads have incremented in_critical
    try:
        both_inside.wait(timeout=3)
    except threading.BrokenBarrierError:
        pass

    count = in_critical
    if count >= 2:
        print(f"  [BUG] {count} threads in critical_section simultaneously! ✓")
        critical_violation.set()

    with in_critical_lock:
        in_critical -= 1

    print(f"  [{name}] <<< leaving critical_section")


# ── Thread 0 ──────────────────────────────────────────────────────────────────
def thread_0() -> None:
    """
    while (true) {
      darkness++;
      evil++;
      if (darkness != 2 && evil != 2) {
        if (fortress.Wait(500)) {
          fortress.Wait();
          Monitor.Enter(sanctum);
          Monitor.Wait(sanctum);
          critical_section();
          Monitor.Exit(sanctum);
        }
      }
    }
    """
    global darkness, evil

    # ── darkness++ (race: read 0, will write 1) ───────────────────────────────
    # Wait until Thread 1 has also read darkness == 0 before either writes
    _fortress_charged.wait()          # fortress must be charged first
    local_darkness = darkness         # read: 0
    _t0_read_darkness.set()
    _t1_read_darkness.wait()          # wait for Thread 1 to also read 0
    darkness = local_darkness + 1     # write: darkness = 1
    print(f"  [Thread 0] darkness++ (race) → darkness = {darkness}")

    # ── evil++ ────────────────────────────────────────────────────────────────
    evil += 1                         # evil = 1
    print(f"  [Thread 0] evil++ → evil = {evil}")

    # ── if (darkness != 2 && evil != 2) ──────────────────────────────────────
    if darkness != 2 and evil != 2:   # 1 != 2 && 1 != 2  → TRUE
        print(f"  [Thread 0] condition TRUE (darkness={darkness}, evil={evil})")

        # ── fortress.Wait(500) — first acquire (counter 2 → 1) ───────────────
        acquired = fortress.acquire(timeout=1)
        assert acquired, "fortress.Wait(500) should succeed"
        print(f"  [Thread 0] fortress.Wait(500) acquired (counter now 1)")

        # ── fortress.Wait() — second acquire (counter 1 → 0) ─────────────────
        fortress.acquire()
        print(f"  [Thread 0] fortress.Wait() acquired (counter now 0)")

        # ── Monitor.Enter(sanctum) + Monitor.Wait(sanctum) ───────────────────
        with sanctum:
            print(f"  [Thread 0] Monitor.Enter(sanctum) — lock acquired")
            _t0_waiting.set()         # signal: Thread 0 is about to Wait
            sanctum.wait()            # releases lock, blocks until Pulse
            print(f"  [Thread 0] Monitor.Wait returned — re-acquired lock")

            # ── critical_section() ────────────────────────────────────────────
            critical_section("Thread0")
        # Monitor.Exit(sanctum) — implicit via 'with'


# ── Thread 1 ──────────────────────────────────────────────────────────────────
def thread_1() -> None:
    """
    while (true) {
      darkness++;
      evil++;
      if (darkness != 2 && evil == 2) {
        Monitor.Enter(sanctum);
        Monitor.Pulse(sanctum);
        Monitor.Exit(sanctum);
        critical_section();
      }
      fortress.Release();
      darkness = 0;
      evil = 0;
    }
    """
    global darkness, evil

    # ── Step 1: run 2 full loops to charge fortress to counter == 2 ──────────
    for i in range(1, 3):
        darkness += 1   # darkness = 1, then 2
        evil += 1       # evil     = 1, then 2
        # neither condition branch fires (darkness == evil == i, not the target)
        fortress.release()   # counter: 0→1, 1→2
        darkness = 0
        evil = 0
        print(f"  [Thread 1] loop {i}: fortress.Release() → counter = {i}")

    print(f"  [Thread 1] fortress charged to 2 — signalling Thread 0")
    _fortress_charged.set()

    # ── darkness++ (race: read 0, will write 1) ───────────────────────────────
    _t0_read_darkness.wait()          # wait for Thread 0 to read darkness first
    local_darkness = darkness         # read: 0  (same value Thread 0 read)
    _t1_read_darkness.set()
    darkness = local_darkness + 1     # write: darkness = 1  (same as Thread 0!)
    print(f"  [Thread 1] darkness++ (race) → darkness = {darkness}")

    # ── evil++ ────────────────────────────────────────────────────────────────
    # Wait until Thread 0 has already incremented evil to 1, then we make it 2
    _t0_waiting.wait()                # Thread 0 must be inside Monitor.Wait first
    evil += 1                         # evil = 2
    print(f"  [Thread 1] evil++ → evil = {evil}")

    # ── if (darkness != 2 && evil == 2) ──────────────────────────────────────
    if darkness != 2 and evil == 2:   # 1 != 2 && 2 == 2  → TRUE
        print(f"  [Thread 1] condition TRUE (darkness={darkness}, evil={evil})")

        # ── Monitor.Enter(sanctum) + Pulse + Exit ────────────────────────────
        with sanctum:
            print(f"  [Thread 1] Monitor.Enter(sanctum) — lock acquired")
            sanctum.notify()          # Monitor.Pulse(sanctum) — wake Thread 0
            print(f"  [Thread 1] Monitor.Pulse(sanctum)")
        # Monitor.Exit(sanctum) — implicit via 'with'
        print(f"  [Thread 1] Monitor.Exit(sanctum)")

        # ── critical_section() ────────────────────────────────────────────────
        critical_section("Thread1")

    # ── fortress.Release(); darkness = 0; evil = 0 ───────────────────────────
    fortress.release()
    darkness = 0
    evil = 0


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Boss Fight — forced race-condition demo")
    print("=" * 55)
    print(f"Initial state: darkness={darkness}, evil={evil}, fortress counter=0\n")

    t0 = threading.Thread(target=thread_0, name="Thread0")
    t1 = threading.Thread(target=thread_1, name="Thread1")

    t1.start()   # Thread 1 must charge the fortress first
    t0.start()

    t0.join()
    t1.join()

    print()
    if critical_violation.is_set():
        print("[RESULT] Bug reproduced: two threads in critical_section at once!")
    else:
        print("[RESULT] Bug was NOT triggered.")
