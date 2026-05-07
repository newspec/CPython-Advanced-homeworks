# Producer-Consumer

import threading
from collections import deque


class Dragon:
    pass


semaphore = threading.Semaphore(0)  # nonsignaled / 0 permits initially
queue: deque = deque()              # number of enqueued items: 0

# Barrier for 2 parties: producer waits here after release(),
# consumer waits here after acquire() — both proceed together,
# but consumer calls popleft() first (queue is still empty).
barrier = threading.Barrier(2)

exception_event = threading.Event()
bug_exception: list = []


def consumer():
    """Thread 0 — consumes dragons from the queue."""
    # acquire() unblocks as soon as producer calls release()
    semaphore.acquire()

    # Rendezvous: wait for producer to also reach the barrier.
    # At this point the producer has called release() but NOT yet append().
    barrier.wait()

    # Now both threads are past the barrier.
    # Producer will call append() — but we call popleft() first
    # because the consumer thread gets scheduled immediately after barrier.wait().
    item = queue.popleft()   # queue is STILL EMPTY → IndexError!
    print(f"[Consumer] Dequeued: {item}")


def producer():
    """Thread 1 — produces dragons and signals the semaphore."""
    # BUG: release semaphore BEFORE appending
    semaphore.release()          # <- signals "item ready" too early

    # Rendezvous: wait for consumer to also reach the barrier.
    # Consumer is now unblocked and waiting here too.
    barrier.wait()

    # Both past the barrier — but consumer already called popleft() above.
    queue.append(Dragon())       # <- too late


def main():
    t0 = threading.Thread(target=consumer, name="Thread-0", daemon=True)
    t1 = threading.Thread(target=producer, name="Thread-1", daemon=True)

    t0.start()
    t1.start()

    t0.join(timeout=5)
    t1.join(timeout=5)


if __name__ == "__main__":
    main()
