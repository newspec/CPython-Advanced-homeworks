"""
Слайд 14: Бенчмарки производительности дескрипторов.

Измеряет время доступа к атрибуту (нс/операцию) для:
  - __slots__
  - Обычный атрибут
  - Non-data дескриптор
  - Data дескриптор
  - staticmethod
  - property
  - Вызов метода
  - __getattribute__
  - classmethod

Запуск: python performance_benchmark.py
"""

import timeit
import tracemalloc

# ── Классы для бенчмарков ──────────────────────────────────────────────────────

class PlainAttr:
    """Обычный класс с атрибутами в __dict__."""
    def __init__(self):
        self.x = 42

    def method(self):
        return self.x

    @property
    def prop(self):
        return self.x

    @staticmethod
    def static_m():
        return 42

    @classmethod
    def class_m(cls):
        return 42

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)


class SlottedAttr:
    """Класс со __slots__."""
    __slots__ = ('x',)

    def __init__(self):
        self.x = 42


class NonDataDesc:
    """Non-data дескриптор: только __get__."""
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return 42


class DataDesc:
    """Data дескриптор: __get__ + __set__."""
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return 42

    def __set__(self, obj, value):
        pass


class WithNonData:
    nd = NonDataDesc()


class WithData:
    d = DataDesc()


# ── Вспомогательная функция ────────────────────────────────────────────────────

def bench(stmt: str, setup: str = "", number: int = 2_000_000) -> float:
    """Возвращает время в наносекундах на одну операцию."""
    t = timeit.timeit(stmt=stmt, setup=setup, number=number, globals=globals())
    return (t / number) * 1e9


# ── Замеры производительности ──────────────────────────────────────────────────

plain_obj    = PlainAttr()
slotted_obj  = SlottedAttr()
nondata_obj  = WithNonData()
data_obj     = WithData()

results = []

# 1. __slots__
ns = bench("slotted_obj.x")
results.append(("__slots__", ns))

# 2. Обычный атрибут
ns = bench("plain_obj.x")
results.append(("Обычный атрибут", ns))

# 3. Non-data дескриптор
ns = bench("nondata_obj.nd")
results.append(("Non-data дескриптор", ns))

# 4. Data дескриптор
ns = bench("data_obj.d")
results.append(("Data дескриптор", ns))

# 5. staticmethod
ns = bench("plain_obj.static_m()")
results.append(("staticmethod()", ns))

# 6. property
ns = bench("plain_obj.prop")
results.append(("property", ns))

# 7. Вызов метода
ns = bench("plain_obj.method()")
results.append(("Вызов метода", ns))

# 8. __getattribute__ (переопределённый)
ns = bench("plain_obj.__getattribute__('x')")
results.append(("__getattribute__", ns))

# 9. classmethod
ns = bench("plain_obj.class_m()")
results.append(("classmethod()", ns))

# ── Замер памяти (tracemalloc) ─────────────────────────────────────────────────

N = 100_000

def measure_memory(cls):
    tracemalloc.start()
    objects = [cls() for _ in range(N)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024, objects

peak_plain,   _objs1 = measure_memory(PlainAttr)
peak_slotted, _objs2 = measure_memory(SlottedAttr)

# ── Вывод ──────────────────────────────────────────────────────────────────────

baseline = next(ns for label, ns in results if label == "Обычный атрибут")

bar_width = 30
max_ns    = max(ns for _, ns in results)

print(f"{'=' * 70}")
print(f"  Бенчмарки производительности дескрипторов")
print(f"  (timeit, 2 000 000 итераций, нс/операцию)")
print(f"{'=' * 70}\n")

print(f"{'Механизм':<25} {'нс/оп':>7}  {'ratio':>6}  {'bar'}")
print(f"{'-' * 70}")

for label, ns in results:
    ratio  = ns / baseline
    filled = int((ns / max_ns) * bar_width)
    bar    = "█" * filled + "░" * (bar_width - filled)
    marker = " ← baseline" if label == "Обычный атрибут" else ""
    print(f"{label:<25} {ns:>6.1f}  {ratio:>5.2f}×  {bar}{marker}")

print(f"\n{'=' * 70}")
print(f"  Потребление памяти (tracemalloc, {N:,} объектов)")
print(f"{'=' * 70}\n")

mem_max = max(peak_plain, peak_slotted)
for label, mb in [("Обычный класс", peak_plain), ("__slots__", peak_slotted)]:
    filled = int((mb / mem_max) * bar_width)
    bar    = "█" * filled + "░" * (bar_width - filled)
    print(f"{label:<20} {mb:>6.1f} МБ  {bar}")

ratio_mem = peak_plain / peak_slotted
print(f"\n  Экономия памяти: {ratio_mem:.2f}×")
print(f"\nГотово.")
