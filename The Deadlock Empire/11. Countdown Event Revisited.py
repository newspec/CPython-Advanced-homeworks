# Countdown Event Revisited — Deadlock Empire (Python reproduction)

import threading
import time


# ── Minimal CountdownEvent ────────────────────────────────────────────────────

class CountdownEvent:
    def __init__(self, count: int) -> None:
        self._count = count
        self._cond  = threading.Condition(threading.Lock())

    def signal(self) -> None:
        with self._cond:
            if self._count <= 0:
                raise RuntimeError(
                    "InvalidOperationException: attempted to decrement "
                    "a countdown timer below zero"
                )
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


# ── Shared state ──────────────────────────────────────────────────────────────

progress = 0
event    = CountdownEvent(3)
captured: list[tuple[str, Exception]] = []
stop     = threading.Event()

# Used only in the first iteration to force the LOAD/STORE split:
# T0 signals after its LOAD so T1 can run both additions+signals,
# then T0 proceeds with its STORE (overwriting T1's result).
t0_loaded = threading.Event()
t1_signalled_twice = threading.Event()
first_iter = True   # flag so the sleep only applies once


# ── Thread bodies ─────────────────────────────────────────────────────────────

def thread0() -> None:
    global progress, first_iter

    while not stop.is_set():
        # Non-atomic read-modify-write, split explicitly to show the race:
        #   temp     = progress + 20   <- LOAD
        #   <--- T1 can run here in the first iteration --->
        #   progress = temp            <- STORE
        temp0 = progress + 20

        if first_iter:
            # Pause between LOAD and STORE so T1 gets to run both its
            # additions and both its Signal() calls before T0 stores.
            t0_loaded.set()
            t1_signalled_twice.wait()
            first_iter = False

        progress = temp0
        print(f"  [T0] progress = {progress}  (+20)")

        event.signal()
        print(f"  [T0] Signal()  -> counter now {event.current_count}")

        event.wait()
        print(f"  [T0] Wait() returned")

        if progress == 100:
            print(f"  [T0] progress == 100 -> Environment.Exit(0)")
            stop.set()
            return


def thread1() -> None:
    global progress

    while not stop.is_set():
        # In the first iteration, wait until T0 has done its LOAD,
        # then run both additions + signals before T0 does its STORE.
        if not t1_signalled_twice.is_set():
            t0_loaded.wait()

        progress = progress + 30
        print(f"  [T1] progress = {progress}  (+30)")

        event.signal()
        print(f"  [T1] Signal() [1st]  -> counter now {event.current_count}")

        progress = progress + 50
        print(f"  [T1] progress = {progress}  (+50)")

        event.signal()
        print(f"  [T1] Signal() [2nd]  -> counter now {event.current_count}")
        
        t1_signalled_twice.set()   # allow T0 to proceed with its STORE

        event.wait()
        print(f"  [T1] Wait() returned")

        if progress == 100:
            print(f"  [T1] progress == 100 -> Environment.Exit(0)")
            stop.set()
            return


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("Countdown Event Revisited — exception via non-atomic STORE")
    print("=" * 64)

    t0 = threading.Thread(target=thread0, name="T0", daemon=True)
    t1 = threading.Thread(target=thread1, name="T1", daemon=True)

    t0.start()
    t1.start()

    t0.join(timeout=3.0)
    t1.join(timeout=3.0)

    print()
