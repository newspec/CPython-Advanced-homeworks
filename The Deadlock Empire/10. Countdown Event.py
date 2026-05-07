# Countdown Event
import threading


# ── Minimal CountdownEvent ────────────────────────────────────────────────────

class CountdownEvent:
    """
    Mirrors System.Threading.CountdownEvent:
      • signal()  — atomically decrements the internal counter.
      • wait()    — blocks until the counter reaches 0.
    """

    def __init__(self, count: int) -> None:
        self._count = count
        self._cond = threading.Condition(threading.Lock())

    def signal(self) -> None:
        with self._cond:
            if self._count <= 0:
                raise RuntimeError("CountdownEvent already at zero")
            self._count -= 1
            if self._count == 0:
                self._cond.notify_all()

    def wait(self) -> None:
        with self._cond:
            while self._count > 0:
                self._cond.wait()

    @property
    def current_count(self) -> int:
        with self._cond:
            return self._count


# ── Reproduce the exact deadlock interleaving from the challenge ──────────────

progress = 0
event = CountdownEvent(3)

# Synchronisation flags to enforce the exact step order
t1_has_read    = threading.Event()   # step 1 done: T1 read progress
t0_has_read    = threading.Event()   # step 2 done: T0 read progress
t1_has_written = threading.Event()   # step 3 done: T1 wrote 30
t0_has_written = threading.Event()   # step 4 done: T0 wrote 20
t0_has_checked = threading.Event()   # step 5 done: T0 signalled
t1_first_check_done = threading.Event()  # step 6 done: T1 signalled


def thread0() -> None:
    global progress

    # Step 2: T0 reads progress (waits until T1 has already read)
    t1_has_read.wait()
    local0 = progress                       # reads 0
    t0_has_read.set()

    # Step 4: T0 writes (waits until T1 has written 30 first)
    t1_has_written.wait()
    progress = local0 + 20                  # writes 20, overwrites T1's 30
    print(f"  [T0] wrote progress = {progress}  (local was {local0}, +20)")
    t0_has_written.set()

    # Step 5: T0 checks and signals
    if progress >= 20:
        event.signal()
        print(f"  [T0] Signal()  → counter now {event.current_count}")
    t0_has_checked.set()

    # Step 10: T0 waits — will block forever (deadlock)
    print(f"  [T0] calling Wait() …")
    event.wait()
    print("  [T0] Wait() returned  ← should NOT happen in deadlock scenario")


def thread1() -> None:
    global progress

    # Step 1: T1 reads progress first
    local1 = progress                       # reads 0
    print(f"  [T1] read  progress = {local1}")
    t1_has_read.set()

    # Step 3: T1 writes (waits until T0 has also read)
    t0_has_read.wait()
    progress = local1 + 30                  # writes 30
    print(f"  [T1] wrote progress = {progress}  (local was {local1}, +30)")
    t1_has_written.set()

    # Step 6: T1 checks first condition (waits until T0 has written and checked)
    t0_has_written.wait()
    t0_has_checked.wait()
    if progress >= 30:                      # progress is now 20 (T0 overwrote!)
        event.signal()
        print(f"  [T1] Signal() [1st check, progress={progress}]"
              f"  → counter now {event.current_count}")
    else:
        print(f"  [T1] {progress} < 30 → no signal [1st check]")
    t1_first_check_done.set()

    # Step 7-9: T1 second addition
    local1b = progress                      # reads 20 (T0's overwritten value)
    progress = local1b + 50                 # writes 70
    print(f"  [T1] wrote progress = {progress}  (local was {local1b}, +50)")

    if progress >= 80:
        event.signal()
        print(f"  [T1] Signal() [2nd check]  → counter now {event.current_count}")
    else:
        print(f"  [T1] {progress} < 80 → no Signal() [2nd check]"
              f"  counter stays at {event.current_count}")

    # Step 10: T1 waits — will block forever (deadlock)
    print(f"  [T1] calling Wait() …")
    event.wait()
    print("  [T1] Wait() returned  ← should NOT happen in deadlock scenario")


if __name__ == "__main__":
    print("=" * 62)
    print("Countdown Event")
    print("=" * 62)

    t0 = threading.Thread(target=thread0, name="T0", daemon=True)
    t1 = threading.Thread(target=thread1, name="T1", daemon=True)

    t1.start()
    t0.start()

    t0.join(timeout=5.0)
    t1.join(timeout=5.0)

    print()
    if t0.is_alive() or t1.is_alive():
        print("✓ DEADLOCK confirmed — both threads are blocked at Wait().")
        print(f"  Final state: progress={progress}, "
              f"event still needs {event.current_count} more signal(s).")
    else:
        print("✗ No deadlock — threads finished (unexpected).")
