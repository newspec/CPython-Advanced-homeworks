# Task: Tutorial 1 - Interface

import threading
import time

# Shared flag (always True — so Thread 1 will always enter critical_section)
flag = True

# Tracks how many threads are currently inside the critical section
threads_in_critical_section = 0
lock_for_counter = threading.Lock()  # only used for printing safely


def business_logic():
    """Simulates some work outside the critical section."""
    time.sleep(0.001)


def critical_section(thread_name):
    """
    The critical section — should only be entered by ONE thread at a time.
    But since there is no mutex/lock here, both threads can enter together.
    """
    global threads_in_critical_section

    # Enter
    with lock_for_counter:
        threads_in_critical_section += 1
        count = threads_in_critical_section

    # If more than 1 thread is here simultaneously — the bug is triggered!
    if count > 1:
        print(f"[{thread_name}] BUG: {count} threads in critical section at the same time!")
    else:
        print(f"[{thread_name}] Entered critical section safely (alone).")

    time.sleep(0.1)  # simulate work inside critical section

    # Exit
    with lock_for_counter:
        threads_in_critical_section -= 1

    print(f"[{thread_name}] Exited critical section.")


def thread_0():
    """
    // This is the first thread.
    business_logic();
    critical_section();   <-- always executes
    business_logic();
    """
    business_logic()
    critical_section("Thread-0")
    business_logic()


def thread_1():
    """
    // This is the second thread.
    if (flag) {
        critical_section();   <-- executes because flag = True
    }
    """
    if flag:
        critical_section("Thread-1")


# --- Run ---
print("=== Tutorial 1: Interface ===")

t0 = threading.Thread(target=thread_0)
t1 = threading.Thread(target=thread_1)

t0.start()
t1.start()

t0.join()
t1.join()

print("\nDone.")
