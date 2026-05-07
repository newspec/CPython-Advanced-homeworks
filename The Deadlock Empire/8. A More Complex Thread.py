# Task: A More Complex Thread

import threading
import time

# RLock matches C# Monitor re-entrant behaviour
mutex  = threading.RLock()
mutex2 = threading.Lock()
mutex3 = threading.Lock()

flag = False

# Synchronisation barriers to force the exact interleaving
# that produces the deadlock deterministically
t0_after_exit_mutex  = threading.Event()  # T0 signals: "I just did Exit(mutex)"
t1_holds_mutex2      = threading.Event()  # T1 signals: "I just acquired mutex2"


def thread_0():
    global flag

    # Step 1: TryEnter(mutex) -> True, count = 1
    acquired = mutex.acquire(blocking=False)
    assert acquired, "TryEnter(mutex) must succeed on first call"
    print("[Thread-0] TryEnter(mutex) = True  | RLock count: 1")

    # Step 2: Enter(mutex3)
    mutex3.acquire()
    print("[Thread-0] Enter(mutex3)")

    # Step 3: Enter(mutex) re-entrant, count = 2
    mutex.acquire()
    print("[Thread-0] Enter(mutex) re-entrant | RLock count: 2")

    # Step 4: critical_section
    print("[Thread-0] critical_section()")

    # Step 5: Exit(mutex) -> count = 1, mutex STILL HELD
    mutex.release()
    print("[Thread-0] Exit(mutex)             | RLock count: 1  ← still held!")

    # Signal Thread-1 to proceed (it was waiting for this moment)
    t0_after_exit_mutex.set()

    # Wait until Thread-1 has grabbed mutex2 before we try to grab it
    # (this forces the exact interleaving from the screenshot)
    t1_holds_mutex2.wait()

    # Step 9: Enter(mutex2) -> DEADLOCK (Thread-1 holds mutex2)
    print("[Thread-0] trying Enter(mutex2)... -> WILL DEADLOCK")
    mutex2.acquire()  # blocks forever
    # never reached:
    flag = False
    mutex2.release()
    mutex3.release()


def thread_1():
    global flag

    # Wait until Thread-0 has done Exit(mutex) and set flag scenario
    # We manually set flag=True here to simulate Thread-0's else-branch having run earlier
    flag = True

    # Wait for Thread-0 to reach the point after Exit(mutex)
    t0_after_exit_mutex.wait()

    # Step 6: flag == True -> if-branch
    print("[Thread-1] flag=True -> if branch")

    # Step 7: Enter(mutex2) -> succeeds
    mutex2.acquire()
    print("[Thread-1] Enter(mutex2)           | holds: mutex2")

    # Signal Thread-0 that we hold mutex2 (so it can now try to acquire it -> deadlock)
    t1_holds_mutex2.set()

    # Step 8: Enter(mutex) -> DEADLOCK (Thread-0 holds mutex, count=1)
    print("[Thread-1] trying Enter(mutex)...  -> WILL DEADLOCK")
    mutex.acquire()  # blocks forever
    # never reached:
    flag = False
    mutex.release()
    mutex2.release()


# --- Run ---
print("=== A More Complex Thread ===")

t0 = threading.Thread(target=thread_0, name="Thread-0", daemon=True)
t1 = threading.Thread(target=thread_1, name="Thread-1", daemon=True)

t0.start()
t1.start()

# Give threads time to reach deadlock
time.sleep(2.0)

if t0.is_alive() and t1.is_alive():
    # Verify: try to acquire mutex2 and mutex from main thread with timeout
    m_free  = mutex.acquire(blocking=True, timeout=0.1)
    m2_free = mutex2.acquire(blocking=True, timeout=0.1)

    if not m_free and not m2_free:
        print()
        print("=" * 60)
        print("BUG: DEADLOCK CONFIRMED!")
        print("  mutex  — held by Thread-0 (RLock count=1), Thread-1 blocked")
        print("  mutex2 — held by Thread-1,                 Thread-0 blocked")
        print("  mutex3 — held by Thread-0")
        print()
        print("  Circular wait: T0 -> mutex2 -> T1 -> mutex -> T0")
        print("=" * 60)
        print("\nDeadlock successfully triggered!")
    else:
        if m_free:  mutex.release()
        if m2_free: mutex2.release()
        print("\nUnexpected: locks were acquirable (deadlock did not occur).")
else:
    print("\nOne or both threads finished unexpectedly.")

print("Done.")
