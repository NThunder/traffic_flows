import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append('.')

from florian import compute_sf, Link as OriginalLink, parse_gtfs as original_parse_gtfs
from lateness_prob_florian import compute_sf_with_lateness_prob, Link as ProbLink, parse_gtfs as prob_parse_gtfs
from utils import parse_gtfs_limited, calculate_headways


def run_comparison_with_gtfs(limit=10000):
    """
    Функция для сравнения оригинального алгоритма Флориана и модифицированного
    с использованием GTFS-данных с ограничением
    """
    print(f"Сравнение оригинального алгоритма Флориана и алгоритма с учетом вероятности опоздания")
    print(f"Используется ограничение на {limit} записей из каждого файла GTFS")
    
    # Используем ограниченный парсинг GTFS
    directory = "improved-gtfs-moscow-official"
    
    # Парсим GTFS с ограничением
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit=limit)
    
    # Рассчитываем интервалы
    departures = calculate_headways(stop_times, active_trips)
    
    # Создаем связи для оригинального алгоритма
    print("Создание связей для оригинального алгоритма...")
    original_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating original links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            link = OriginalLink(from_node, to_node, route_id, travel_cost, headway)
            original_links.append(link)

    # Создаем связи для вероятностного алгоритма
    print("Создание связей для вероятностного алгоритма...")
    prob_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating prob links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            # В реальной реализации нужно рассчитать std_travel_time на основе исторических данных
            # Для примера используем фиксированное значение
            std_travel_time = mean_travel_time * 0.2  # 20% от среднего времени

            link = ProbLink(from_node, to_node, route_id, mean_travel_time, std_travel_time, headway)
            prob_links.append(link)

    # Параметры для тестирования
    # Выберем первую остановку в all_stops как destination и origin
    stops_list = list(all_stops)
    if len(stops_list) < 2:
        print("Недостаточно остановок для тестирования")
        return None, None
    
    destination = stops_list[0]
    origin = stops_list[1] if len(stops_list) > 1 else stops_list[0]
    od_matrix = {origin: {destination: 1000}}  # 1000 пассажиров из origin в destination
    arrival_deadline = 45  # дедлайн в 45 минут
    
    print(f"Тестирование на маршруте: {origin} -> {destination}")
    print(f"Количество остановок: {len(all_stops)}")
    print(f"Количество связей (original): {len(original_links)}")
    print(f"Количество связей (prob): {len(prob_links)}")
    
    # Вычисляем результаты с помощью модифицированного алгоритма
    print("Вычисление результатов с вероятностным алгоритмом...")
    result_lateness_prob = compute_sf_with_lateness_prob(
        prob_links, all_stops, destination, od_matrix, arrival_deadline
    )
    
    print(f"\nРезультаты модифицированного алгоритма (вероятность опоздания):")
    print(f"Вероятность прибытия вовремя из {origin}: {result_lateness_prob.strategy.labels.get(origin, 'N/A')}")
    print(f"Вероятность прибытия вовремя в целевой узел: {result_lateness_prob.strategy.labels.get(destination, 'N/A')}")
    
    # Вычисляем результаты с помощью оригинального алгоритма
    print("Вычисление результатов с оригинальным алгоритмом...")
    original_result = compute_sf(original_links, all_stops, destination, od_matrix)
    
    print(f"\nРезультаты оригинального алгоритма Флориана:")
    print(f"Обобщенные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Обобщенные затраты в целевом узле: {original_result.strategy.labels.get(destination, 'N/A')}")
    
    # Сравниваем стратегии
    print(f"\nСравнение стратегий:")
    print(f"Оригинальный алгоритм - минимальные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Новый алгоритм - вероятность прибытия вовремя из {origin}: {result_lateness_prob.strategy.labels.get(origin, 'N/A')}")
    
    # Создаем визуализацию
    create_comparison_visualization(original_result, result_lateness_prob, all_stops, origin, destination)
    
    return original_result, result_lateness_prob

def convert_time(time_str):
    """Преобразование времени из GTFS формата (копия из других модулей)"""
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

def create_comparison_visualization(original_result, prob_result, all_stops, origin, destination):
    """
    Создает визуализацию сравнения двух алгоритмов
    """
    # Подготовка данных для визуализации
    # Выбираем только несколько ключевых остановок для отображения
    stops_to_show = list(all_stops)[:10]  # Показываем только первые 10 остановок
    
    # Получаем значения меток для обеих стратегий
    original_labels = [original_result.strategy.labels.get(stop, 0) for stop in stops_to_show]
    prob_labels = [prob_result.strategy.labels.get(stop, 0) for stop in stops_to_show]
    
    # Создаем график
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # График 1: Сравнение меток узлов
    x = np.arange(len(stops_to_show))
    width = 0.35
    
    ax1.bar(x - width/2, original_labels, width, label='Оригинальный алгоритм (затраты)', alpha=0.8)
    ax1.bar(x + width/2, prob_labels, width, label='Алгоритм с вероятностью опоздания', alpha=0.8)
    
    ax1.set_xlabel('Остановки')
    ax1.set_ylabel('Значение метки')
    ax1.set_title('Сравнение значений меток узлов')
    ax1.set_xticks(x)
    ax1.set_xticklabels(stops_to_show, rotation=45, ha="right")
    ax1.legend()
    
    # График 2: Сравнение объемов на узлах
    original_volumes = [original_result.volumes.nodes.get(stop, 0) for stop in stops_to_show]
    prob_volumes = [prob_result.volumes.nodes.get(stop, 0) for stop in stops_to_show]
    
    ax2.bar(x - width/2, original_volumes, width, label='Оригинальный алгоритм', alpha=0.8)
    ax2.bar(x + width/2, prob_volumes, width, label='Алгоритм с вероятностью опоздания', alpha=0.8)
    
    ax2.set_xlabel('Остановки')
    ax2.set_ylabel('Объемы')
    ax2.set_title('Сравнение объемов на узлах')
    ax2.set_xticks(x)
    ax2.set_xticklabels(stops_to_show, rotation=45, ha="right")
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('gtfs_comparison_results.png', dpi=300, bbox_inches='tight')
    print(f"\nГрафики сравнения сохранены в файл 'gtfs_comparison_results.png'")
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

def run_extended_comparison_with_gtfs(limit=5000):
    """
    Расширенное сравнение с различными временными дедлайнами на GTFS-данных
    """
    print("\n" + "="*70)
    print("РАСШИРЕННОЕ СРАВНЕНИЕ С РАЗЛИЧНЫМИ ВРЕМЕННЫМИ ДЕДЛАЙНАМИ (на GTFS-данных)")
    print("="*70)
    
    # Используем ограниченный парсинг GTFS
    directory = "improved-gtfs-moscow-official"
    
    # Парсим GTFS с ограничением
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit=limit)
    
    # Рассчитываем интервалы
    departures = calculate_headways(stop_times, active_trips)
    
    # Создаем связи для оригинального алгоритма
    print("Создание связей для оригинального алгоритма...")
    original_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating original links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            link = OriginalLink(from_node, to_node, route_id, travel_cost, headway)
            original_links.append(link)

    # Создаем связи для вероятностного алгоритма
    print("Создание связей для вероятностного алгоритма...")
    prob_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating prob links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            # В реальной реализации нужно рассчитать std_travel_time на основе исторических данных
            # Для примера используем фиксированное значение
            std_travel_time = mean_travel_time * 0.2  # 20% от среднего времени

            link = ProbLink(from_node, to_node, route_id, mean_travel_time, std_travel_time, headway)
            prob_links.append(link)

    # Параметры для тестирования
    # Выберем первую остановку в all_stops как destination и вторую как origin
    stops_list = list(all_stops)
    if len(stops_list) < 2:
        print("Недостаточно остановок для тестирования")
        return
    
    destination = stops_list[0]
    origin = stops_list[1] if len(stops_list) > 1 else stops_list[0]
    od_matrix = {origin: {destination: 1000}}  # 1000 пассажиров из origin в destination
    
    # Тестируем с разными временными дедлайнами
    deadlines = [20, 30, 45, 60, 75]
    
    print("Сравнение при разных временных дедлайнах:")
    print("Дедлайн (мин) | Вероятность успеха (новый) | Затраты (оригинал)")
    print("-" * 60)
    
    results = []
    
    for deadline in deadlines:
        print(f"Обработка дедлайна: {deadline} минут")
        
        # Вычисляем результаты с помощью модифицированного алгоритма
        prob_result = compute_sf_with_lateness_prob(
            prob_links, all_stops, destination, od_matrix, deadline
        )
        
        # Вычисляем результаты с помощью оригинального алгоритма
        original_result = compute_sf(original_links, all_stops, destination, od_matrix)
        
        prob_success = prob_result.strategy.labels.get(origin, 0)
        original_cost = original_result.strategy.labels.get(origin, 0)
        
        print(f"{deadline:11d} | {prob_success:23.4f} | {original_cost:16.4f}")
        
        results.append((deadline, prob_success, original_cost))
    
    # Визуализация зависимости
    if results:
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
        plt.savefig('gtfs_deadline_comparison.png', dpi=300, bbox_inches='tight')
        print(f"\nГрафик зависимости от дедлайна сохранен в файл 'gtfs_deadline_comparison.png'")
        plt.show()


if __name__ == "__main__":
    # Выполняем основное сравнение с GTFS-данными
    original_result, prob_result = run_comparison_with_gtfs(limit=5000)
    
    # Выполняем расширенное сравнение
    run_extended_comparison_with_gtfs(limit=500)
    
    # Анализируем влияние на утренние потоки
    analyze_morning_rush_implications()
    
    print("\nСравнение завершено. Результаты визуализированы и проанализированы.")