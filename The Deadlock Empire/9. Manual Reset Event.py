# Task: Manual Reset Event

import threading

# Shared state
counter = 0
sync = threading.Event()   # starts nonsignaled

print_lock = threading.Lock()
bug_found  = threading.Event()

# Barriers to force the exact interleaving deterministically
t0_is_waiting        = threading.Event()  # T0 signals: "I am inside sync.wait()"
t1_completed_set     = threading.Event()  # T1 signals: "I called sync.Set()"
t1_counter_is_odd    = threading.Event()  # T1 signals: "I did first counter++ of next iteration"
t0_ready_to_check    = threading.Event()  # T0 signals: "sync.wait() returned, about to check"


def thread_0():
    """
    // Thread 0:
    while (true) {
        sync.Wait();
        if (counter % 2 == 1) {
            Debug.Assert(false);
        }
    }
    """
    global counter

    # Signal that we are about to block on sync.wait()
    t0_is_waiting.set()

    sync.wait()              # blocks until Thread-1 calls sync.Set()

    # sync.wait() returned -- signal Thread-1 to proceed with next iteration
    t0_ready_to_check.set()

    # Wait for Thread-1 to make counter odd before we check
    t1_counter_is_odd.wait()

    val = counter
    with print_lock:
        print(f"[Thread-0] sync.wait() passed, checking counter = {val}")

    if val % 2 == 1:
        with print_lock:
            print(f"[Thread-0] BUG: Debug.Assert(false) triggered! counter = {val}")
        bug_found.set()
    else:
        with print_lock:
            print(f"[Thread-0] counter = {val} (even, no bug this time)")


def thread_1():
    """
    // Thread 1:
    while (true) {
        sync.Reset();
        counter++;
        counter++;
        sync.Set();
    }
    """
    global counter

    # Wait until Thread-0 is blocked inside sync.wait()
    t0_is_waiting.wait()

    # --- First iteration ---
    sync.clear()                          # sync.Reset()
    with print_lock:
        print(f"[Thread-1] sync.Reset()")

    # Non-atomic counter++ (first)
    temp = counter + 1                    # READ + ADD
    counter = temp                        # WRITE
    with print_lock:
        print(f"[Thread-1] first counter++  -> counter = {counter}")

    # Non-atomic counter++ (second)
    temp = counter + 1                    # READ + ADD
    counter = temp                        # WRITE
    with print_lock:
        print(f"[Thread-1] second counter++ -> counter = {counter}")

    sync.set()                            # sync.Set() -> Thread-0 wakes up
    with print_lock:
        print(f"[Thread-1] sync.Set()       -> Thread-0 unblocked")

    # Wait until Thread-0 has woken up from sync.wait() but not yet checked counter
    t0_ready_to_check.wait()

    # --- Second iteration (partial) ---
    # Thread-0 has woken up but not yet evaluated counter % 2
    # We now do Reset + first counter++ to make counter odd
    sync.clear()                          # sync.Reset()
    with print_lock:
        print(f"[Thread-1] sync.Reset() (second iteration)")

    # Non-atomic counter++ -> counter becomes odd (3)
    temp = counter + 1                    # READ + ADD
    counter = temp                        # WRITE
    with print_lock:
        print(f"[Thread-1] first counter++ of next iteration -> counter = {counter} (odd!)")

    # Signal Thread-0 that counter is now odd -- it can proceed with the check
    t1_counter_is_odd.set()


# --- Run ---
print("=== Manual Reset Event ===")

t0 = threading.Thread(target=thread_0, daemon=True)
t1 = threading.Thread(target=thread_1, daemon=True)

t0.start()
t1.start()

t0.join(timeout=3)
t1.join(timeout=3)

if bug_found.is_set():
    print(f"\nBug successfully triggered! Final counter = {counter}")
else:
    print("\nBug not triggered.")

print("Done.")
