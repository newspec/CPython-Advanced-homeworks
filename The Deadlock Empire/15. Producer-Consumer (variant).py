# Producer-Consumer (variant)

import threading


class Golem:
    pass


# ── Non-thread-safe Queue that exposes its internal inconsistency ─────────────

class NonThreadSafeQueue:
    """Mimics C# Queue<T> internal behaviour during Enqueue.

    Enqueue is split into 3 observable steps so we can force a context
    switch between step 2 (count incremented) and step 3 (element stored).
    """

    def __init__(self):
        self._storage: list = []
        self._count: int = 0          # separate counter — can diverge from storage!

    @property
    def count(self) -> int:
        return self._count            # Consumer reads this in the if-check

    def enqueue(self, item, pause_event: threading.Event | None = None):
        """Three-step enqueue — NOT atomic."""
        # Step 1: queue enters an inconsistent state (nothing visible yet)
        # (in a real impl this might be resizing an internal array)

        # Step 2: count increases — consumer can now see count > 0,
        #         but the element is NOT in _storage yet!
        self._count += 1
        print(f"[Producer] Step 2: count={self._count}, "
              f"storage len={len(self._storage)}  <- inconsistent state")

        # ── forced context switch ──────────────────────────────────────────
        # Signal the consumer that count > 0, then wait so the consumer
        # runs Dequeue() before we finish storing the element.
        if pause_event is not None:
            pause_event.set()         # wake consumer: "count is now > 0"
            # Yield the GIL so consumer thread runs next.
            # We use a short sleep to guarantee the switch happens here.
            import time
            time.sleep(0.01)
        # ──────────────────────────────────────────────────────────────────

        # Step 3: element is actually stored — queue returns to consistent state
        self._storage.append(item)
        print(f"[Producer] Step 3: count={self._count}, "
              f"storage len={len(self._storage)}  <- consistent again")

    def dequeue(self):
        """Dequeue — reads from _storage, NOT from _count."""
        if len(self._storage) == 0:
            raise IndexError(
                "Dequeue called on empty storage! "
                f"count={self._count} but storage is empty — "
                "inconsistent state caused by concurrent Enqueue."
            )
        item = self._storage.pop(0)
        self._count -= 1
        return item


# ── shared state ──────────────────────────────────────────────────────────────
queue = NonThreadSafeQueue()

# Event: producer signals consumer after incrementing count (step 2).
count_incremented = threading.Event()


# ── threads ───────────────────────────────────────────────────────────────────

def producer():
    """Mirrors: while (true) { queue.Enqueue(new Golem()); }"""
    while True:
        # Pass the event so enqueue pauses between step 2 and step 3.
        queue.enqueue(Golem(), pause_event=count_incremented)
        break   # one iteration is enough to demonstrate the bug


def consumer():
    """Mirrors: while (true) { if (queue.Count > 0) { queue.Dequeue(); } }"""
    while True:
        # Wait until producer has incremented count (step 2).
        count_incremented.wait()

        # Check: count > 0  <- passes because producer incremented it
        if queue.count > 0:
            print(f"[Consumer] Check passed: count={queue.count} > 0")
            # ── ACT ──
            # Producer is paused between step 2 and step 3:
            # count is 1, but _storage is still empty → IndexError!
            item = queue.dequeue()
            print(f"[Consumer] Dequeued: {item}")
        return


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    t_consumer = threading.Thread(target=consumer, name="Consumer", daemon=True)
    t_producer = threading.Thread(target=producer, name="Producer", daemon=True)

    t_producer.start()
    t_consumer.start()

    t_producer.join(timeout=5)
    t_consumer.join(timeout=5)


if __name__ == "__main__":
    main()
