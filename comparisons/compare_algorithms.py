import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

# Добавляем текущую директорию в путь для импорта
sys.path.append('.')

from florian import compute_sf, Link as OriginalLink, find_optimal_strategy, assign_demand
from lateness_prob_florian import compute_sf_with_lateness_prob, Link as ProbLink, parse_sample_data


def run_comparison():
    """
    Функция для сравнения оригинального алгоритма Флориана и модифицированного
    """
    print("Сравнение оригинального алгоритма Флориана и алгоритма с учетом вероятности опоздания")
    
    # Используем наши тестовые данные
    all_links, all_stops = parse_sample_data()
    
    # Параметры для тестирования
    destination = 'C'
    od_matrix = {'A': {'C': 1000}}  # 1000 пассажиров из A в C
    arrival_deadline = 25  # дедлайн в 25 минут
    
    # Вычисляем результаты с помощью модифицированного алгоритма
    result_lateness_prob = compute_sf_with_lateness_prob(
        all_links, all_stops, destination, od_matrix, arrival_deadline
    )
    
    print(f"\nРезультаты модифицированного алгоритма (вероятность опоздания):")
    print(f"Вероятности прибытия вовремя из каждой остановки: {result_lateness_prob.strategy.labels}")
    print(f"Объемы на узлах: {result_lateness_prob.volumes.nodes}")
    
    # Преобразуем наши данные для оригинального алгоритма
    # Используем среднее время в качестве стоимости, а интервал - как headway
    original_links = [
        OriginalLink(link.from_node, link.to_node, link.route_id, link.mean_travel_time, link.headway)
        for link in all_links
    ]
    
    original_result = compute_sf(original_links, all_stops, destination, od_matrix)
    
    print(f"\nРезультаты оригинального алгоритма Флориана:")
    print(f"Обобщенные затраты: {original_result.strategy.labels}")
    print(f"Объемы на узлах: {original_result.volumes.nodes}")
    
    # Сравниваем стратегии
    print(f"\nСравнение стратегий:")
    print(f"Оригинальный алгоритм - минимальные затраты из A: {original_result.strategy.labels.get('A', 'N/A')}")
    print(f"Новый алгоритм - вероятность прибытия вовремя из A: {result_lateness_prob.strategy.labels.get('A', 'N/A')}")
    
    # Создаем визуализацию
    create_comparison_visualization(original_result, result_lateness_prob, all_stops)
    
    return original_result, result_lateness_prob


def create_comparison_visualization(original_result, prob_result, all_stops):
    """
    Создает визуализацию сравнения двух алгоритмов
    """
    # Подготовка данных для визуализации
    stops = list(all_stops)
    
    # Получаем значения меток для обеих стратегий
    original_labels = [original_result.strategy.labels.get(stop, 0) for stop in stops]
    prob_labels = [prob_result.strategy.labels.get(stop, 0) for stop in stops]
    
    # Создаем график
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # График 1: Сравнение меток узлов
    x = np.arange(len(stops))
    width = 0.35
    
    ax1.bar(x - width/2, original_labels, width, label='Оригинальный алгоритм (затраты)', alpha=0.8)
    ax1.bar(x + width/2, prob_labels, width, label='Алгоритм с вероятностью опоздания', alpha=0.8)
    
    ax1.set_xlabel('Остановки')
    ax1.set_ylabel('Значение метки')
    ax1.set_title('Сравнение значений меток узлов')
    ax1.set_xticks(x)
    ax1.set_xticklabels(stops)
    ax1.legend()
    
    # График 2: Сравнение объемов на узлах
    original_volumes = [original_result.volumes.nodes.get(stop, 0) for stop in stops]
    prob_volumes = [prob_result.volumes.nodes.get(stop, 0) for stop in stops]
    
    ax2.bar(x - width/2, original_volumes, width, label='Оригинальный алгоритм', alpha=0.8)
    ax2.bar(x + width/2, prob_volumes, width, label='Алгоритм с вероятностью опоздания', alpha=0.8)
    
    ax2.set_xlabel('Остановки')
    ax2.set_ylabel('Объемы')
    ax2.set_title('Сравнение объемов на узлах')
    ax2.set_xticks(x)
    ax2.set_xticklabels(stops)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('comparison_results.png', dpi=300, bbox_inches='tight')
    print(f"\nГрафики сравнения сохранены в файл 'comparison_results.png'")
    plt.show()


def analyze_morning_rush_implications():
    """
    Анализирует, как новый подход может повлиять на моделирование утренних потоков
    """
    print("\n" + "="*70)
    print("АНАЛИЗ ВЛИЯНИЯ НОВОГО ПОДХОДА НА МОДЕЛИРОВАНИЕ УТРЕННИХ ПОТОКОВ")
    print("="*70)
    
    print("""
    Классический алгоритм Флориана минимизирует ожидаемые обобщенные затраты,
    включая время ожидания, время в пути и штрафы за пересадки. 
    
    Новый подход минимизирует вероятность опоздания, что особенно актуально
    для утренних поездок на работу/учебу, когда людям важно прибыть к определенному
    времени с высокой вероятностью.
    
    ОСНОВНЫЕ ОТЛИЧИЯ:
    
    1. Учет неопределенности:
       - Оригинальный: предполагает детерминированные времена
       - Новый: учитывает вариабельность времени в пути (дисперсию)
    
    2. Целевая функция:
       - Оригинальный: минимизация среднего времени
       - Новый: максимизация вероятности прибытия вовремя
    
    3. Поведение пассажиров:
       - Оригинальный: пассажиры выбирают маршрут с минимальными ожидаемыми затратами
       - Новый: пассажиры выбирают маршрут, который дает максимальную вероятность 
                прибытия до заданного времени
    
    ПРЕИМУЩЕСТВА НОВОГО ПОДХОДА ДЛЯ УТРЕННИХ ПОТОКОВ:
    
    - Более реалистичное моделирование поведения пассажиров, которые стремятся 
      избежать опоздания на работу/учебу
    - Учет вариабельности транспортных потоков в утренние часы
    - Возможность моделирования "безопасного" выбора маршрута, когда пассажиры 
      выбирают более надежный, но возможно более длинный маршрут, чтобы избежать риска опоздания
    - Учет не только среднего времени, но и надежности маршрута
    
    ПРИМЕР СЦЕНАРИЯ:
    Допустим, у пассажира есть выбор между:
    a) Быстрым, но ненадежным маршрутом (15 мин в среднем, но с высокой вариацией)
    b) Более медленным, но надежным маршрутом (20 мин, с низкой вариацией)
    
    Оригинальный алгоритм предпочтет вариант (a) из-за меньшего среднего времени.
    Новый алгоритм может выбрать вариант (b), если дедлайн близок и надежность важнее скорости.
    """)

def run_extended_comparison():
    """
    Расширенное сравнение с различными временными дедлайнами
    """
    print("\n" + "="*70)
    print("РАСШИРЕННОЕ СРАВНЕНИЕ С РАЗЛИЧНЫМИ ВРЕМЕННЫМИ ДЕДЛАЙНАМИ")
    print("="*70)
    
    # Используем наши тестовые данные
    all_links, all_stops = parse_sample_data()
    
    # Параметры для тестирования
    destination = 'C'
    od_matrix = {'A': {'C': 1000}}  # 1000 пассажиров из A в C
    
    # Тестируем с разными временными дедлайнами
    deadlines = [20, 25, 30, 35, 40]
    
    print("Сравнение при разных временных дедлайнах:")
    print("Дедлайн (мин) | Вероятность успеха (новый) | Затраты (оригинал)")
    print("-" * 60)
    
    results = []
    
    for deadline in deadlines:
        # Вычисляем результаты с помощью модифицированного алгоритма
        prob_result = compute_sf_with_lateness_prob(
            all_links, all_stops, destination, od_matrix, deadline
        )
        
        # Преобразуем данные для оригинального алгоритма
        original_links = [
            OriginalLink(link.from_node, link.to_node, link.route_id, link.mean_travel_time, link.headway)
            for link in all_links
        ]
        
        original_result = compute_sf(original_links, all_stops, destination, od_matrix)
        
        prob_success = prob_result.strategy.labels.get('A', 0)
        original_cost = original_result.strategy.labels.get('A', 0)
        
        print(f"{deadline:11d} | {prob_success:23.4f} | {original_cost:16.4f}")
        
        results.append((deadline, prob_success, original_cost))
    
    # Визуализация зависимости
    deadlines_vals, prob_vals, cost_vals = zip(*results)
    
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(deadlines_vals, prob_vals, 'b-o', label='Вероятность прибытия вовремя')
    plt.xlabel('Временной дедлайн (мин)')
    plt.ylabel('Вероятность')
    plt.title('Зависимость вероятности успеха от дедлайна')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(deadlines_vals, cost_vals, 'r-s', label='Обобщенные затраты')
    plt.xlabel('Временной дедлайн (мин)')
    plt.ylabel('Затраты')
    plt.title('Зависимость затрат от дедлайна')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('deadline_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\nГрафик зависимости от дедлайна сохранен в файл 'deadline_comparison.png'")
    plt.show()


if __name__ == "__main__":
    # Выполняем основное сравнение
    original_result, prob_result = run_comparison()
    
    # Выполняем расширенное сравнение
    run_extended_comparison()
    
    # Анализируем влияние на утренние потоки
    analyze_morning_rush_implications()
    
    print("\nСравнение завершено. Результаты визуализированы и проанализированы.")