# Semaphores — The Deadlock Empire, Challenge 13

import threading

# ── shared state ──────────────────────────────────────────────────────────────
semaphore = threading.Semaphore(0)   # counter starts at 0

in_critical = 0
in_critical_lock = threading.Lock()  # only to safely read/write the counter
violation_detected = threading.Event()

# Barriers used to choreograph the exact interleaving
# barrier_A: both threads reach the point just before their first semaphore op
barrier_A = threading.Barrier(2)
# barrier_B: Thread-0 is blocked in acquire(); Thread-1 is about to time out
barrier_B = threading.Barrier(2)
# barrier_C: Thread-1 has called Release() in else-branch; Thread-0 can proceed
barrier_C = threading.Barrier(2)
# barrier_D: Thread-0 is inside critical_section(); Thread-1 about to re-acquire
barrier_D = threading.Barrier(2)


def critical_section(name: str) -> None:
    global in_critical
    with in_critical_lock:
        in_critical += 1
        count = in_critical

    if count > 1:
        print(f"  *** BUG: {name} entered critical_section while another "
              f"thread is already inside (in_critical={count})! ***")
        violation_detected.set()

    # Stay inside long enough for the other thread to enter too
    violation_detected.wait(timeout=0.5)

    with in_critical_lock:
        in_critical -= 1


# ── Thread 0 ──────────────────────────────────────────────────────────────────
def thread0() -> None:
    """
    Choreographed version of:
        while True:
            semaphore.Wait()
            critical_section()
            semaphore.Release()
    """
    # Step 1: both threads ready
    barrier_A.wait()

    # Step 2: Thread-0 calls acquire() — will block because semaphore=0
    # We need Thread-1 to time out first (barrier_B lets Thread-1 know
    # Thread-0 is about to block).
    barrier_B.wait()          # signal Thread-1: "I'm about to block"
    semaphore.acquire()       # blocks until Thread-1's else-branch releases

    # Step 4: Thread-0 unblocked, enters critical section
    # Signal Thread-1 it can now re-acquire
    barrier_D.wait()
    critical_section("Thread-0")
    semaphore.release()


# ── Thread 1 ──────────────────────────────────────────────────────────────────
def thread1() -> None:
    """
    Choreographed version of:
        while True:
            if semaphore.Wait(500 ms):
                critical_section()
                semaphore.Release()
            else:
                semaphore.Release()
    """
    # Step 1: both threads ready
    barrier_A.wait()

    # Step 3: wait until Thread-0 is about to block, then do a very short
    # Wait() that is guaranteed to time out (semaphore is still 0).
    barrier_B.wait()          # Thread-0 is about to call acquire()

    acquired = semaphore.acquire(timeout=0.05)   # times out — semaphore=0
    if acquired:
        # Should NOT happen in this choreography
        critical_section("Thread-1 (unexpected acquire)")
        semaphore.release()
    else:
        # BUG: release without having acquired -> semaphore 0 -> 1
        semaphore.release()
        print("  Thread-1: timed out -> called Release() in else-branch "
              "(semaphore inflated to 1)")

    # Step 5: Thread-0 has been unblocked and is entering CS.
    acquired2 = semaphore.acquire(timeout=0.05)   # semaphore=0 -> times out again
    if acquired2:
        # Thread-0 already released; just enter CS normally (no bug this round)
        critical_section("Thread-1 (normal)")
        semaphore.release()
    else:
        # BUG again: second spurious Release -> semaphore 0 -> 1
        semaphore.release()
        print("  Thread-1: timed out again -> Release() again "
              "(semaphore inflated to 1 while Thread-0 is in CS)")

    # Now Thread-1 acquires the coin that was just spuriously added
    barrier_D.wait()          # wait until Thread-0 is inside critical_section
    semaphore.acquire()       # succeeds immediately (semaphore=1)
    print("  Thread-1: acquired semaphore while Thread-0 is still in CS -> BUG!")
    critical_section("Thread-1")
    semaphore.release()


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Semaphores race-condition demo")
    print("=" * 60)
    print("semaphore starts at 0.")
    print("Thread-1's else-branch calls Release() on timeout,")
    print("inflating the semaphore counter without holding a coin.\n")

    t0 = threading.Thread(target=thread0, name="Thread-0", daemon=True)
    t1 = threading.Thread(target=thread1, name="Thread-1", daemon=True)

    t0.start()
    t1.start()

    triggered = violation_detected.wait(timeout=10)

    t0.join(timeout=2)
    t1.join(timeout=2)

    print()
    if triggered:
        print("Result: ✓ race condition reproduced — two threads were in the "
              "critical section at the same time.")
    else:
        print("Result: ✗ no violation detected.")
