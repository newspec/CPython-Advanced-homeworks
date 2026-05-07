# Task: Confused Counter

import threading
import time

# Shared variables (intentionally unprotected — no lock!)
first = 0
second = 0

print_lock = threading.Lock()
bug_found = threading.Event()  # signals when the failure instruction is hit


def business_logic():
    """Simulates some work — also acts as a delay to widen the race window."""
    time.sleep(0.001)


def thread_0():
    """
    // Thread 0:
    business_logic();
    first++;
    second++;
    if (second == 2 && first != 2) {
        Debug.Assert(false);   <-- FAILURE: should never happen!
    }
    """
    global first, second

    business_logic()

    # Non-atomic first++ : READ phase
    temp_first = first + 1
    # At this point Thread 1 also reads first=0 (race window)
    time.sleep(0.004)          # hold the stale value long enough for T1 to also read
    first = temp_first         # WRITE: first = 1  (T1 will also write 1 -> first stays 1)

    # Non-atomic second++ : READ -> WRITE (no gap — T0 finishes second before T1 reads it)
    temp_second = second + 1   # reads 0
    second = temp_second       # writes 1  (T1 will read 1 and write 2)

    # Wait for T1 to finish writing second=2 before checking the condition
    time.sleep(0.005)

    # Failure instruction — should NEVER be reached under normal conditions
    if second == 2 and first != 2:
        with print_lock:
            print(f"[Thread-0] FAILURE: Debug.Assert(false) triggered!")
            print(f"           second={second}, first={first}")
            print(f"           second==2 and first!=2 — impossible state reached!")
        bug_found.set()


def thread_1():
    """
    // Thread 1:
    business_logic();
    first++;
    second++;
    """
    global first, second

    business_logic()

    # Non-atomic first++ : READ phase — races with T0's read above
    temp_first = first + 1     # also reads 0 while T0 is sleeping with stale value
    time.sleep(0.006)          # sleep past T0's write so T0 already wrote first=1
    first = temp_first         # WRITE: first = 1 again -> first stays 1, not 2!

    # Non-atomic second++ : READ -> WRITE after T0 already wrote second=1
    time.sleep(0.002)          # ensure T0 has already written second=1
    temp_second = second + 1   # reads 1
    second = temp_second       # writes 2  -> second == 2, first == 1 -> FAILURE condition!


def run_once():
    """Run one iteration of both threads and check the result."""
    global first, second
    first = 0
    second = 0

    t0 = threading.Thread(target=thread_0)
    t1 = threading.Thread(target=thread_1)

    t0.start()
    t1.start()

    t0.join()
    t1.join()


# --- Run repeatedly until the bug appears ---
print("=== Confused Counter ===")

attempt = 0
while not bug_found.is_set():
    attempt += 1
    run_once()

    if attempt % 10 == 0:
        with print_lock:
            print(f"  Attempt {attempt}: first={first}, second={second} — no bug yet...")

    if attempt >= 500:
        print("Bug not triggered in 500 attempts (try running again).")
        break

if bug_found.is_set():
    print(f"\nBug successfully triggered on attempt {attempt}!")

print("Done.")
