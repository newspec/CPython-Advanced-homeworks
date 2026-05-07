# Task: Simple Counter

import threading
import time

# Shared counter (intentionally unprotected — no lock!)
counter = 0

# For detecting the bug
threads_in_critical_section = 0
print_lock = threading.Lock()


def critical_section(thread_name):
    """No protection — both threads can be here simultaneously."""
    global threads_in_critical_section

    threads_in_critical_section += 1
    count = threads_in_critical_section

    with print_lock:
        if count > 1:
            print(f"[{thread_name}] BUG: {count} threads in critical section simultaneously!")
        else:
            print(f"[{thread_name}] Entered critical section (alone). counter={counter}")

    time.sleep(0.05)  # simulate work inside critical section
    threads_in_critical_section -= 1

    with print_lock:
        print(f"[{thread_name}] Exited critical section.")


def five_headed_dragon():
    """
    // Five-Headed Dragon:
    while (true) {
        counter++;
        if (counter == 5) {
            critical_section();
        }
    }
    """
    global counter

    while True:
        # Non-atomic counter++ simulated explicitly
        temp = counter + 1
        time.sleep(0.001)  
        counter = temp  

        if counter == 5:
            critical_section("Five-Headed Dragon")


def three_headed_dragon():
    """
    // Three-Headed Dragon:
    while (true) {
        counter++;
        if (counter == 3) {
            critical_section();
        }
    }
    """
    global counter

    while True:
        # Non-atomic counter++ simulated explicitly
        temp = counter + 1
        time.sleep(0.001)  
        counter = temp        

        if counter == 3:
            critical_section("Three-Headed Dragon")


# --- Run ---
print("=== Simple Counter ===")

t0 = threading.Thread(target=five_headed_dragon, daemon=True)
t1 = threading.Thread(target=three_headed_dragon, daemon=True)

t0.start()
t1.start()

# Let it run for a short time
time.sleep(1)

print("Done.")
