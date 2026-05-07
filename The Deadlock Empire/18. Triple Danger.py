# Triple Danger

import threading
import collections

# ── shared state ──────────────────────────────────────────────────────────────
conduit = threading.Lock()
energy_bursts: collections.deque = collections.deque()

# Synchronisation helpers that let us reproduce the exact interleaving
# described in the task without relying on random scheduling luck.
_electricity_checked = threading.Event()   # Electricity passed the if-check
_fire_may_run        = threading.Event()   # Fire is allowed to drain the queue
_fire_done           = threading.Event()   # Fire finished draining
_electricity_may_lock = threading.Event()  # Electricity may now acquire the lock


# ── threads ───────────────────────────────────────────────────────────────────

def sorcerer() -> None:
    """Enqueues energy bursts under the lock (runs once to seed the queue)."""
    # Do this for initial conditions
    with conduit:
        for _ in range(3):
            energy_bursts.append(object())   # Enqueue(new EnergyBurst())
    print(f"[Sorcerer]     enqueued 3 items  -> queue size: {len(energy_bursts)}")


def dragon_head_electricity() -> None:
    """
    Checks the queue length WITHOUT the lock, then acquires the lock and
    dequeues.  The gap between the check and the lock acquisition is exactly
    where the race condition lives.
    """
    # ── if (energyBursts.Count > 0) ──────────────────────────────────────────
    if len(energy_bursts) > 0:
        print(f"[Electricity]  if-check passed  -> queue size: {len(energy_bursts)}")

        # Signal that we passed the check, then PAUSE before taking the lock.
        # This simulates the context-switch that happens between the if-check
        # and Monitor.Enter(conduit).
        _electricity_checked.set()
        _electricity_may_lock.wait()   # wait until Fire has drained the queue

        # ── Monitor.Enter(conduit) ────────────────────────────────────────────
        with conduit:
            print(f"[Electricity]  acquired lock   -> queue size: {len(energy_bursts)}")
            # ── energyBursts.Dequeue() ────────────────────────────────────────
            item = energy_bursts.popleft()   # IndexError if queue is empty!
            print(f"[Electricity]  dequeued item   -> queue size: {len(energy_bursts)}")
            # lightning_bolts(terrifying=True)
            print("[Electricity] lightning bolts!")


def dragon_head_fire() -> None:
    """
    Waits until Electricity has passed its if-check, then drains the entire
    queue three times (simulating 3 full iterations of the Fire loop).
    """
    _electricity_checked.wait()   # wait for Electricity to pass the if-check

    for i in range(1, 4):
        # ── if (energyBursts.Count > 0) ──────────────────────────────────────
        if len(energy_bursts) > 0:
            # ── Monitor.Enter(conduit) ────────────────────────────────────────
            with conduit:
                if len(energy_bursts) > 0:   # re-check inside the lock
                    energy_bursts.popleft()
                    print(f"[Fire]         iteration {i}: dequeued -> queue size: {len(energy_bursts)}")
                    # fireball(mighty=True)

    print(f"[Fire]         done draining   -> queue size: {len(energy_bursts)}")
    # Now let Electricity try to dequeue from the (now empty) queue.
    _electricity_may_lock.set()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    sorcerer()   # seed the queue with 3 items

    t_elec = threading.Thread(target=dragon_head_electricity, name="Electricity")
    t_fire = threading.Thread(target=dragon_head_fire,        name="Fire")

    t_elec.start()
    t_fire.start()

    t_elec.join()
    t_fire.join()


if __name__ == "__main__":
    print("=" * 60)
    print("Triple Danger — reproducing the race condition")
    print("=" * 60)

    main()
