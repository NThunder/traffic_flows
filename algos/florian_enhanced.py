from utils import *
import math
from algos.florian import assign_demand, calculate_flow_volumes, SFResult, Strategy

def find_optimal_strategy_enhanced(all_links, all_stops, destination):
    """
    Полностью переработанная версия алгоритма Spiess-Florian с правильным учетом начала поездки и внутри-маршрутных перемещений.
    
    Используем состояние (route_id, is_continuation), где:
    - route_id: идентификатор маршрута
    - is_continuation: True, если пассажир уже в поездке на этом маршруте (ожидание не нужно)
                      False, если пассажир только начинает поездку на этом маршруте или делает пересадку (ожидание нужно)
    """
    if VERBOSE:
        print("Enhanced Initialization")
    
    # Для каждой остановки будем хранить минимальные затраты для каждого состояния (маршрут, продолжение_поездки)
    # u[stop] = {(route_id, is_continuation): min_cost, ...}
    u = {}
    f = {}  # частоты для каждого состояния в узле
    
    for stop in all_stops:
        u[stop] = {}
        f[stop] = {}

    # Устанавливаем конечную точку
    u[destination] = {('END', False): 0.0}  # специальное состояние для конечной точки
    f[destination] = {('END', False): 0.0}

    overline_a = []  # привлекательное множество связей

    # Группируем связи по конечной остановке
    links_by_to_node = {}
    for link in all_links:
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    # Инициализируем приоритетную очередь
    pq = PriorityQueue()
    for link in all_links:
        if link.to_node in all_stops:
            # Берем минимальные затраты из конечной остановки этой связи
            min_cost_to_dest = min(u[link.to_node].values()) if u[link.to_node] and u[link.to_node].values() else MATH_INF
            pq.push(link, min_cost_to_dest + link.travel_cost)

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node  # текущая остановка
        j = a.to_node    # следующая остановка
        route_id = a.route_id  # маршрут, которым мы едем
        
        if i not in all_stops or j not in all_stops:
            continue

        # Обрабатываем все возможные состояния в узле j
        for (j_route, j_is_continuation) in list(u[j].keys()):
            if j_route == 'END':
                # Это конечная точка
                cost_on_route_at_j = u[j][(j_route, j_is_continuation)]
                cost_via_a = a.travel_cost  # просто время в пути
                # Обновляем узел i как начало новой поездки (ожидание нужно)
                current_cost_at_i = u[i].get((route_id, False), MATH_INF)
                
                if cost_via_a < current_cost_at_i:
                    u[i][(route_id, False)] = cost_via_a
                    freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
                    f[i][(route_id, False)] = freq
                    overline_a.append(a)

            elif j_route == route_id:
                # Это продолжение поездки на том же маршруте
                cost_on_route_at_j = u[j][(j_route, j_is_continuation)]
                # При продолжении поездки на том же маршруте ожидание не добавляется
                cost_via_a = a.travel_cost + cost_on_route_at_j
                # Обновляем узел i как продолжение поездки на маршруте route_id
                current_cost_at_i = u[i].get((route_id, True), MATH_INF)
                
                if cost_via_a < current_cost_at_i:
                    u[i][(route_id, True)] = cost_via_a
                    freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
                    f[i][(route_id, True)] = freq
                    overline_a.append(a)

            else:
                # Это переход на другой маршрут (пересадка)
                cost_on_route_at_j = u[j][(j_route, j_is_continuation)]
                # При пересадке нужно учитывать время ожидания
                wait_time = a.headway / 2.0 if a.headway > 0 else 0
                cost_via_a = wait_time + a.travel_cost + cost_on_route_at_j
                # Обновляем узел i как начало поездки на новом маршруте (ожидание нужно)
                current_cost_at_i = u[i].get((route_id, False), MATH_INF)
                
                if cost_via_a < current_cost_at_i:
                    u[i][(route_id, False)] = cost_via_a
                    freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
                    f[i][(route_id, False)] = freq
                    overline_a.append(a)

    # Преобразуем результат в старый формат для совместимости
    # Берем минимальные затраты для каждой остановки по всем маршрутам и состояниям
    final_u = {}
    final_f = {}
    for stop in all_stops:
        if stop in u and u[stop] and u[stop].values():
            final_u[stop] = min(u[stop].values())
            final_f[stop] = sum(f[stop].values()) if stop in f else 0.0
        else:
            final_u[stop] = MATH_INF
            final_f[stop] = 0.0
    
    return Strategy(final_u, final_f, overline_a)


def compute_sf_enhanced(all_links, all_stops, destination, od_matrix):
    ops = find_optimal_strategy_enhanced(all_links, all_stops, destination)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)