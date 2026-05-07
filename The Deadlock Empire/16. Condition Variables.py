# Condition Variables

import threading
import collections
import time

# ── shared state ──────────────────────────────────────────────────────────────
mutex = threading.Condition(threading.Lock())
queue: collections.deque = collections.deque()

bug_triggered = threading.Event()   # set when the bug fires


# ── helpers that mirror the C# Monitor API ────────────────────────────────────

def monitor_enter():
    """Acquire the underlying lock (Condition wraps a Lock)."""
    mutex.acquire()


def monitor_exit():
    """Release the underlying lock."""
    mutex.release()


def monitor_wait():
    """
    Atomically release the lock and wait for a notify.
    Mirrors Monitor.Wait(mutex).
    """
    mutex.wait()


def monitor_pulse_all():
    """
    Wake all threads waiting on the condition.
    Mirrors Monitor.PulseAll(mutex).
    """
    mutex.notify_all()


# ── Thread 0 & Thread 1 — consumers (buggy: uses `if`, not `while`) ──────────

def consumer(thread_id: int) -> None:
    """
    Buggy consumer: uses a plain `if` to check the queue.
    After being woken by PulseAll, it does NOT re-check whether the queue
    is still non-empty, so it may call dequeue() on an empty queue.
    """
    while not bug_triggered.is_set():
        monitor_enter()
        if len(queue) == 0:          # ← BUG: should be `while`, not `if`
            monitor_wait()

        # At this point the thread assumes the queue is non-empty,
        # but another consumer may have already taken the item.
        if len(queue) == 0:
            # Reproduce the InvalidOperationException from C#
            print(
                f"[Thread {thread_id}] BUG: tried to dequeue from an "
                "empty queue! (InvalidOperationException)"
            )
            bug_triggered.set()
            return

        item = queue.popleft()       # queue.Dequeue()
        print(f"[Thread {thread_id}] dequeued {item}")

        monitor_exit()               # Monitor.Exit(mutex)

        time.sleep(0)                    # yield to scheduler


# ── Thread 2 — producer ───────────────────────────────────────────────────────

def producer() -> None:
    """
    Producer: enqueues exactly ONE item then wakes ALL waiting consumers.
    Using PulseAll (notify_all) is what triggers the bug — both consumers
    wake up but only one item is available.
    """
    # Give consumers time to block on Wait before we produce anything.
    time.sleep(0.05)

    while not bug_triggered.is_set():
        monitor_enter()
        try:
            queue.append(42)             # queue.Enqueue(42)
            print("[Thread 2] enqueued 42, calling PulseAll …")
            monitor_pulse_all()          # Monitor.PulseAll(mutex)
        finally:
            monitor_exit()               # Monitor.Exit(mutex)

        # Slow the producer down so consumers have time to both wake up
        # before the next item is enqueued.
        time.sleep(0.1)


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    t0 = threading.Thread(target=consumer, args=(0,), daemon=True)
    t1 = threading.Thread(target=consumer, args=(1,), daemon=True)
    t2 = threading.Thread(target=producer,            daemon=True)

    t0.start()
    t1.start()
    t2.start()

    # Wait until the bug fires (or give up after 10 s)
    triggered = bug_triggered.wait(timeout=10)

    if triggered:
        print("\nBug successfully reproduced: dequeue on empty queue.")
    else:
        print("Bug did not fire within the timeout — try running again.")
