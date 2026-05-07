# Task: Boolean Flags Are Enough For Everyone

import threading
import time

# Shared flag (intentionally unprotected — no lock!)
flag = False

# For detecting the bug
threads_in_critical_section = 0
print_lock = threading.Lock()
bug_found = threading.Event()  # signals when both threads enter critical section


def critical_section(thread_name):
    """No protection — both threads can be here simultaneously."""
    global threads_in_critical_section

    threads_in_critical_section += 1
    count = threads_in_critical_section

    with print_lock:
        if count > 1:
            print(f"[{thread_name}] BUG: {count} threads in critical section simultaneously!")
            bug_found.set()
        else:
            pass  # silent in normal case to reduce noise

    time.sleep(0.01)  # simulate work inside critical section
    threads_in_critical_section -= 1


def first_army():
    """
    // First Army:
    while (flag != false) { ; }   <-- spin-wait until flag is False
    flag = true;                  <-- "claim" the section (weak guard!)
    critical_section();
    flag = false;                 <-- release
    """
    global flag

    # Spin-wait: busy loop until flag becomes False
    while flag != False:
        time.sleep(0)  # yield GIL so Second Army can run

    # Race window: Second Army may ALSO have exited the while loop here!
    time.sleep(0)  # widen the race window: yield GIL before setting flag

    flag = True       # "claim" — but this is NOT atomic with the check above!
    critical_section("First Army")
    flag = False      # release


def second_army():
    """
    // Second Army:
    while (flag != false) { ; }   <-- spin-wait until flag is False
    flag = true;                  <-- "claim" the section (weak guard!)
    critical_section();
    flag = false;                 <-- release
    """
    global flag

    # Spin-wait: busy loop until flag becomes False
    while flag != False:
        time.sleep(0)  # yield GIL so First Army can run

    # Race window: First Army may ALSO have exited the while loop here!
    time.sleep(0)  # widen the race window: yield GIL before setting flag

    flag = True       # "claim" — but this is NOT atomic with the check above!
    critical_section("Second Army")
    flag = False      # release


def run_once():
    """Run one iteration: each thread does one pass through the critical section."""
    global flag, threads_in_critical_section
    flag = False
    threads_in_critical_section = 0

    t0 = threading.Thread(target=first_army)
    t1 = threading.Thread(target=second_army)

    t0.start()
    t1.start()

    t0.join()
    t1.join()


# --- Run repeatedly until the bug appears ---
print("=== Boolean Flags Are Enough For Everyone ===")
print("Trying to get both threads into the critical section simultaneously\n")

attempt = 0
while not bug_found.is_set():
    attempt += 1
    run_once()

    if attempt % 50 == 0:
        with print_lock:
            print(f"  Attempt {attempt}: no bug yet...")

    if attempt >= 1000:
        print("Bug not triggered in 1000 attempts (try running again).")
        break

if bug_found.is_set():
    print(f"\nBug successfully triggered on attempt {attempt}!")

print("Done.")
