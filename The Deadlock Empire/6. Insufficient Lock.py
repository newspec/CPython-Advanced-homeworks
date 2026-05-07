# Task: Insufficient Lock

import threading
import time

# Shared variables
mutex = threading.Lock()
i = 0

# For detecting simultaneous entry into critical section
threads_in_critical_section = 0
print_lock = threading.Lock()
bug_found = threading.Event()


def critical_section(thread_name):
    global threads_in_critical_section

    threads_in_critical_section += 1
    count = threads_in_critical_section

    if count > 1:
        with print_lock:
            print(f"[{thread_name}] BUG: {count} threads in critical section simultaneously!")
        bug_found.set()
    
    time.sleep(0.001)
    threads_in_critical_section -= 1


def thread_0():
    """
    // Thread 0:
    while (true) {
        Monitor.Enter(mutex);
        i = i + 2;
        critical_section();
        if (i == 5) {
            Debug.Assert(false);
        }
        Monitor.Exit(mutex);
    }
    """
    global i

    while not bug_found.is_set():
        mutex.acquire()

        # Non-atomic i = i + 2
        temp = i + 2        # READ + ADD
        # context switch may happen here
        i = temp            # WRITE

        critical_section("Thread-0")

        if i == 5:
            with print_lock:
                print(f"[Thread-0] BUG: Debug.Assert(false) triggered!")
            bug_found.set()

        mutex.release()


def thread_1():
    """
    // Thread 1:
    while (true) {
        Monitor.Enter(mutex);
        i = i - 1;
        critical_section();
        Monitor.Exit(mutex);
    }
    """
    global i

    while not bug_found.is_set():
        mutex.acquire()

        # Non-atomic i = i - 1
        temp = i - 1        # READ + SUB
        # context switch may happen here
        i = temp            # WRITE

        critical_section("Thread-1")

        mutex.release()


# --- Run ---
print("=== Insufficient Lock ===")

t0 = threading.Thread(target=thread_0, daemon=True)
t1 = threading.Thread(target=thread_1, daemon=True)

t0.start()
t1.start()

bug_found.wait(timeout=5)

if bug_found.is_set():
    print(f"\nBug successfully triggered!")
else:
    print("\nBug not triggered in 5 seconds (try running again).")

print("Done.")
