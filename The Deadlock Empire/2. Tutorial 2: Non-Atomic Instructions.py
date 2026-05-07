# Task: Tutorial 2 - Non-Atomic Instructions

import threading
import time

# Shared variable (intentionally unprotected)
a = 0

# For detecting the bug
threads_in_critical_section = 0
print_lock = threading.Lock()


def critical_section(thread_name):
    """No protection — both threads can be here simultaneously."""
    global threads_in_critical_section

    threads_in_critical_section += 1
    count = threads_in_critical_section

    if count > 1:
        with print_lock:
            print(f"[{thread_name}] BUG: {count} threads in critical section simultaneously!")
    else:
        with print_lock:
            print(f"[{thread_name}] Entered critical section (alone).")

    time.sleep(0.1)  # simulate work
    threads_in_critical_section -= 1


def thread_0():
    """
    // Thread 0:
    a = a + 1;
    if (a == 1) {
        critical_section();
    }
    """
    global a

    # Simulating non-atomic a = a + 1 explicitly:
    temp = a + 1
    time.sleep(0.05)
    a = temp

    with print_lock:
        print(f"[Thread-0] a = {a}")

    if a == 1:
        critical_section("Thread-0")


def thread_1():
    """
    // Thread 1:
    // Expand the following instruction:
    a = a + 1;
    if (a == 1) {
        critical_section();
    }
    """
    global a

    # Simulating non-atomic a = a + 1 explicitly:
    temp = a + 1
    time.sleep(0.05)
    a = temp

    with print_lock:
        print(f"[Thread-1] a = {a}")

    if a == 1:
        critical_section("Thread-1")


# --- Run ---
print("=== Tutorial 2: Non-Atomic Instructions ===")

t0 = threading.Thread(target=thread_0)
t1 = threading.Thread(target=thread_1)

# Start both threads almost simultaneously to provoke the race
t0.start()
t1.start()

t0.join()
t1.join()

print("Done.")
