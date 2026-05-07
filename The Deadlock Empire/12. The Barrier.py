# The Barrier

import threading

# ── shared state ──────────────────────────────────────────────────────────────
fireball_charge_lock = threading.Lock()
fireball_charge = 0

# Barrier with only 2 participants — the key bug (should be 3)
barrier = threading.Barrier(2)

bug_triggered = threading.Event()   # set when the assertion fires


# ── helpers ───────────────────────────────────────────────────────────────────
def atomic_increment():
    """Simulate Interlocked.Increment — atomic add-1, returns new value."""
    global fireball_charge
    with fireball_charge_lock:
        fireball_charge += 1
        return fireball_charge


def fireball():
    pass  # placeholder — just marks "launch fireball"


# ── threads ───────────────────────────────────────────────────────────────────
def thread_0():
    """
    while (true) {
        Interlocked.Increment(ref fireballCharge);
        barrier.SignalAndWait();
        if (fireballCharge < 2) { Debug.Assert(false); }
        fireball();
    }
    """
    global fireball_charge
    while not bug_triggered.is_set():
        atomic_increment()

        barrier.wait()

        # ← race window: another thread may reset fireballCharge here
        if fireball_charge < 2:
            print(
                f"[Thread 0] BUG! fireballCharge = {fireball_charge} < 2  "
                f"→ Debug.Assert(false) triggered!"
            )
            bug_triggered.set()
            break

        fireball()


def thread_1():
    """
    while (true) {
        Interlocked.Increment(ref fireballCharge);
        barrier.SignalAndWait();
    }
    """
    while not bug_triggered.is_set():
        atomic_increment()

        barrier.wait()


def thread_2():
    """
    while (true) {
        Interlocked.Increment(ref fireballCharge);
        barrier.SignalAndWait();
        barrier.SignalAndWait();
        fireballCharge = 0;
    }
    """
    global fireball_charge
    while not bug_triggered.is_set():
        atomic_increment()

        barrier.wait()   # 1st wait
        barrier.wait()   # 2nd wait — pairs with a *different* thread!

        # non-atomic reset — another thread may read stale value after this
        fireball_charge = 0


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting 'The Barrier' race-condition demo …")

    threads = [
        threading.Thread(target=thread_0, name="Thread-0", daemon=True),
        threading.Thread(target=thread_1, name="Thread-1", daemon=True),
        threading.Thread(target=thread_2, name="Thread-2", daemon=True),
    ]

    for t in threads:
        t.start()

    # Wait until the bug fires (or give up after 10 s)
    triggered = bug_triggered.wait(timeout=10)

    # Abort any threads still blocked on the barrier
    barrier.abort()

    for t in threads:
        t.join(timeout=1)
