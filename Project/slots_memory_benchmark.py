"""
Слайд 9: __slots__ — измерение реального потребления памяти.

Сравниваем:
  - Обычный класс (с __dict__)
  - Класс со __slots__

Запуск: python slots_memory_benchmark.py
"""

import sys
import tracemalloc

N = 100_000  # количество объектов


# ── Обычный класс ──────────────────────────────────────────────────────────────
class PointDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y


# ── Класс со __slots__ ─────────────────────────────────────────────────────────
class PointSlots:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y


# ── Вспомогательная функция ────────────────────────────────────────────────────
def measure(cls, n=N):
    """Создаёт n объектов cls и возвращает (peak_mb, size_one_bytes)."""
    tracemalloc.start()
    objects = [cls(i, i * 2) for i in range(n)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    size_one = sys.getsizeof(objects[0])
    peak_mb = peak / 1024 / 1024
    return peak_mb, size_one, objects  # objects держим живыми до конца замера


# ── Замеры ─────────────────────────────────────────────────────────────────────
print(f"{'=' * 55}")
print(f"  Сравнение памяти: обычный класс vs __slots__")
print(f"  Количество объектов: {N:,}")
print(f"{'=' * 55}\n")

# Обычный класс
peak_dict, size_dict, _ = measure(PointDict)

# Класс со __slots__
peak_slots, size_slots, _ = measure(PointSlots)

# ── Вывод ──────────────────────────────────────────────────────────────────────
print(f"{'Метрика':<35} {'PointDict':>12} {'PointSlots':>12}")
print(f"{'-' * 60}")
print(f"{'sys.getsizeof(obj), байт':<35} {size_dict:>12} {size_slots:>12}")
print(f"{'Пик памяти (tracemalloc), МБ':<35} {peak_dict:>11.1f} {peak_slots:>11.1f}")
print(f"{'Экономия памяти':<35} {'—':>12} {peak_dict / peak_slots:>10.1f}×")
print()

# ── Дополнительно: наличие __dict__ ───────────────────────────────────────────
obj_dict  = PointDict(1, 2)
obj_slots = PointSlots(1, 2)

has_dict_plain = str(hasattr(obj_dict,  '__dict__'))
has_dict_slots = str(hasattr(obj_slots, '__dict__'))
slot_x_type    = type(PointSlots.__dict__['x']).__name__

print(f"{'Атрибут':<35} {'PointDict':>12} {'PointSlots':>12}")
print(f"{'-' * 60}")
print(f"{'hasattr(obj, __dict__)':<35} {has_dict_plain:>12} {has_dict_slots:>12}")
print(f"{'type(cls.__dict__[x])':<35} {'—':>12} {slot_x_type:>12}")
print()

# ── Попытка добавить произвольный атрибут ─────────────────────────────────────
print("Попытка добавить obj.z = 3 для PointSlots:")
try:
    obj_slots.z = 3
except AttributeError as e:
    print(f"  AttributeError: {e}")

print()
print("Готово.")
