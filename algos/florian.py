from utils import *
import math

# Оригинальный Spiess-Florian (минимизация ожидаемого времени)

def find_optimal_strategy(all_links, all_stops, destination):
    """
    Улучшенная версия алгоритма Spiess-Florian с учетом внутри-маршрутных перемещений.
    Основное изменение: при перемещении по одному и тому же маршруту не добавляется
    время ожидания, в отличие от пересадок между маршрутами.
    """
    if VERBOSE:
        print("Initialization")
    
    # Для каждой остановки будем хранить минимальные затраты для каждого маршрута
    # u[stop] = {route_id: min_cost, ...} - минимальные затраты до цели, находясь на данном маршруте
    u = {}
    f = {}  # частоты для каждого маршрута в узле
    
    for stop in all_stops:
        u[stop] = {}
        f[stop] = {}

    # Устанавливаем конечную точку
    u[destination] = {None: 0.0}  # специальное значение для конечной точки
    f[destination] = {None: 0.0}

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

        # Проверяем, можем ли мы улучшить значение для узла i на маршруте route_id
        # Находим минимальные затраты до цели, находясь на маршруте route_id в узле j
        cost_on_route_at_j = MATH_INF
        if j in u and route_id in u[j]:
            cost_on_route_at_j = u[j][route_id]
        elif j in u and u[j]:  # если для конкретного маршрута нет данных, берем минимальные
            cost_on_route_at_j = min(u[j].values())
        elif j == destination:
            cost_on_route_at_j = 0.0
        
        if cost_on_route_at_j < MATH_INF:
            # Это перемещение по тому же маршруту - добавляем только время в пути
            cost_via_a = cost_on_route_at_j + a.travel_cost
        elif j == destination:
            # Если это конечная остановка
            cost_via_a = a.travel_cost
        else:
            # Невозможно добраться до цели из узла j
            continue

        # Проверяем, улучшит ли это наше значение для узла i на маршруте route_id
        current_cost_at_i_for_route = u[i].get(route_id, MATH_INF)
        
        if cost_via_a < current_cost_at_i_for_route:
            # Обновляем значение
            u[i][route_id] = cost_via_a
            
            # Обновляем частоту для этого маршрута в узле i
            freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
            f[i][route_id] = freq

            if VERBOSE:
                print(f"Update: node {i}, route {route_id}, cost = {cost_via_a}")

            # Добавляем связь в привлекательное множество
            overline_a.append(a)

            # Обновляем приоритеты для связей, входящих в узел i
            if i in links_by_to_node:
                for prev_link in links_by_to_node[i]:
                    if prev_link.to_node in all_stops and prev_link.from_node in all_stops:
                        # Рассчитываем новый приоритет для связи prev_link
                        min_cost_at_i = min(u[i].values()) if u[i] and u[i].values() else MATH_INF
                        new_priority = min_cost_at_i + prev_link.travel_cost
                        pq.update(prev_link, new_priority)

        # Также проверяем возможность пересадки - когда пассажир прибывает в узел i на одном маршруте
        # и может пересесть на маршрут a.route_id
        for prev_route in u[j]:
            if prev_route != route_id and prev_route is not None:
                # Есть возможность пересесть с маршрута prev_route на route_id в узле i
                cost_on_prev_route_at_j = u[j][prev_route]
                
                # При пересадке нужно учитывать время ожидания
                wait_time = a.headway / 2.0 if a.headway > 0 else 0  # среднее время ожидания
                total_cost_if_transfer = cost_on_prev_route_at_j + wait_time + a.travel_cost
                
                if total_cost_if_transfer < current_cost_at_i_for_route:
                    u[i][route_id] = total_cost_if_transfer
                    f[i][route_id] = freq
                    
                    if VERBOSE:
                        print(f"Transfer improvement: from route {prev_route} to {route_id} at node {i}")
                    
                    # Обновляем приоритеты для связей, входящих в узел i
                    if i in links_by_to_node:
                        for prev_link in links_by_to_node[i]:
                            if prev_link.to_node in all_stops and prev_link.from_node in all_stops:
                                min_cost_at_i = min(u[i].values()) if u[i] and u[i].values() else MATH_INF
                                new_priority = min_cost_at_i + prev_link.travel_cost
                                pq.update(prev_link, new_priority)

    # Преобразуем результат в старый формат для совместимости
    # Берем минимальные затраты для каждой остановки по всем маршрутам
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

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending (labels[to] + travel_cost)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.labels[a.to_node] + a.travel_cost))

    return calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination)


def compute_sf(all_links, all_stops, destination, od_matrix):
    ops = find_optimal_strategy(all_links, all_stops, destination)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def parse_gtfs(directory, limit=10000):
    stop_times, active_trips, all_stops, stop_names, route_names = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)
    

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory, 100000)

    print("Ищем пару связанных остановок...")
    origin, destination = find_connected_od_pair_with_min_hops(all_links)

    if origin is None or destination is None:
        raise ValueError("Не удалось найти ни одной пары остановок с путём между ними!")

    print(f"Найдена пара: origin={origin}, destination={destination}")

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin in origins_reaching_dest:
        if origin != destination:
            demand = random.uniform(50.0, 500.0)
            od_matrix[origin] = {destination: demand}

    print(f"OD-матрица создана: {len(od_matrix)} origin → {destination} (случайный спрос)")
    result = compute_sf(all_links, all_stops, destination, od_matrix)