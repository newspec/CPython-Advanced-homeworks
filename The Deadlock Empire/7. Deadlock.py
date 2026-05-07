# Task: Deadlock

import threading
import time

# Two shared mutexes (no ordering -> deadlock possible)
mutex  = threading.Lock()
mutex2 = threading.Lock()

print_lock = threading.Lock()


def critical_section(thread_name):
    with print_lock:
        print(f"[{thread_name}] Entered critical section.")
    time.sleep(0.001)
    with print_lock:
        print(f"[{thread_name}] Exited critical section.")


def thread_0():
    """
    // Thread 0:
    Monitor.Enter(mutex);
    Monitor.Enter(mutex2);
    critical_section();
    Monitor.Exit(mutex);
    Monitor.Exit(mutex2);
    """
    with print_lock:
        print("[Thread-0] Acquiring mutex...")
    mutex.acquire()
    with print_lock:
        print("[Thread-0] Acquired mutex. Now acquiring mutex2...")

    # context switch may happen here -> Thread-1 acquires mutex2 first
    time.sleep(0.1)

    with print_lock:
        print("[Thread-0] Trying to acquire mutex2... (may block here)")
    mutex2.acquire()   # will block forever if Thread-1 holds mutex2

    critical_section("Thread-0")

    mutex.release()
    mutex2.release()


def thread_1():
    """
    // Thread 1:
    Monitor.Enter(mutex2);
    Monitor.Enter(mutex);
    critical_section();
    Monitor.Exit(mutex2);
    Monitor.Exit(mutex);
    """
    with print_lock:
        print("[Thread-1] Acquiring mutex2...")
    mutex2.acquire()
    with print_lock:
        print("[Thread-1] Acquired mutex2. Now acquiring mutex...")

    # context switch may happen here -> Thread-0 is already waiting for mutex2
    time.sleep(0.1)

    with print_lock:
        print("[Thread-1] Trying to acquire mutex... (may block here)")
    mutex.acquire()    # will block forever if Thread-0 holds mutex

    critical_section("Thread-1")

    mutex2.release()
    mutex.release()


# --- Run ---
print("=== Deadlock ===")

t0 = threading.Thread(target=thread_0, daemon=True)
t1 = threading.Thread(target=thread_1, daemon=True)

t0.start()
t1.start()

# Wait long enough to observe the deadlock
time.sleep(3)

# Check if threads are still alive (deadlocked)
if t0.is_alive() and t1.is_alive():
    print("\nBUG: Both threads are still blocked -> DEADLOCK confirmed!")
elif t0.is_alive():
    print("\nThread-0 is still blocked.")
elif t1.is_alive():
    print("\nThread-1 is still blocked.")
else:
    print("\nNo deadlock this time (try running again).")

print("Done")
