from utils import *
import math
from scipy import stats

def find_optimal_strategy(all_links, all_stops, destination, T=60.0):
    """
    Модифицированная версия Spiess-Florian: максимизация вероятности прибытия вовремя (reliability).
    
    mean_var[i] = (mean_time, variance_time) — параметры нормального распределения
                  оставшегося времени от узла i до destination.
    R_i = P(оставшееся время ≤ T) = norm.cdf(T - mean, scale=sqrt(variance))
    """
    if VERBOSE:
        print("Initialization for arrive time model")
    
    mean_var = {}
    freqs = {}
    for stop in all_stops:
        if stop == destination:
            mean_var[stop] = (0.0, 0.0)   # mean=0, var=0 → R=1.0
        else:
            mean_var[stop] = (math.inf, 0.0)  # недостижим → R=0.0
        freqs[stop] = 0.0
    
    attractive_set = []
    
    incoming_links = {}
    for link in all_links:
        incoming_links.setdefault(link.to_node, []).append(link)
    
    pq = PriorityQueue2()
    
    if destination in incoming_links:
        for link in incoming_links[destination]:
            i = link.from_node
            freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
            
            mean_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
            var_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
            
            tent_mean = mean_wait + link.travel_cost  + mean_var[destination][0]
            tent_var = var_wait + mean_var[destination][1]
            
            tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(max(tent_var, 1e-8)))
            
            pq.push(link, -tent_r, tent_mean)
    
    while True:
        entry = pq.pop()
        if entry[0] is None:
            break
        link, priority, orig_priority = entry
        current_priority_r = -priority
        mean_travel_time_priority = orig_priority
        
        i = link.from_node
        j = link.to_node
        
        curr_mean, curr_var = mean_var[i]
        if curr_mean == math.inf:
            current_r = 0.0
        else:
            current_r = stats.norm.cdf(T - curr_mean, scale=math.sqrt(max(curr_var, 1e-8)))
        
        # sum_uc = mean_travel_time_priority
        
        if abs(current_r - current_priority_r) <= EPSILON and curr_mean < mean_travel_time_priority:
            continue
        
        if current_r > current_priority_r:
            continue
        
        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  current_r >= current_priority_r : {current_r} < {current_priority_r} - FALSE")
        
        freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
        mean_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
        var_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
        
        new_mean_via_link = mean_wait + link.travel_cost + mean_var[j][0]
        new_var_via_link = var_wait + mean_var[j][1]
        
        if VERBOSE:
            print(f"  f_a = {freq}")
            print(f"  mean_wait = {mean_wait}")
            print(f"  var_wait = {var_wait}")
            print(f"  new_mean_via_link = {new_mean_via_link}")
            print(f"  new_var_via_link = {new_var_via_link}")
        
        if freqs[i] == 0.0:
            updated_mean = new_mean_via_link
            updated_var = new_var_via_link
            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))
        else:
            total_freq = freqs[i] + freq
            
            updated_mean = (freqs[i] * mean_var[i][0] + freq * new_mean_via_link) / total_freq
            
            m2_old = mean_var[i][1] + mean_var[i][0]**2
            m2_new = new_var_via_link + new_mean_via_link**2
            
            updated_m2 = (freqs[i] * m2_old + freq * m2_new) / total_freq
            updated_var = updated_m2 - updated_mean**2
            updated_var = max(updated_var, 0.0)
            
            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))
        
        if updated_r > current_r + 1e-6 or (abs(updated_r - current_r) <= EPSILON and updated_mean < curr_mean):
            mean_var[i] = (updated_mean, updated_var)
            freqs[i] += freq
            attractive_set.append(link)
            
            if VERBOSE:
                print(f"Updated node {i}: R = {updated_r:.4f}, mean = {updated_mean:.2f}, std = {math.sqrt(updated_var):.2f}")
            
            if i in incoming_links:
                for prev_link in incoming_links[i]:
                    prev_freq = INFINITE_FREQUENCY if prev_link.headway <= 0 else 1.0 / prev_link.headway
                    
                    prev_mean_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                    prev_tent_mean = prev_mean_wait + prev_link.travel_cost  + updated_mean
                    
                    prev_var_wait = prev_mean_wait  # (1.0 / prev_freq)**2 / 12.0
                    prev_tent_var = prev_var_wait  + updated_var
                    
                    prev_tent_var = max(prev_tent_var, 1e-8)
                    prev_tent_r = stats.norm.cdf(T - prev_tent_mean, scale=math.sqrt(prev_tent_var))
                    
                    pq.update(prev_link, -prev_tent_r, prev_tent_mean)
    
    return Strategy(mean_var, freqs, attractive_set)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending expected time (proxy)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.labels[a.to_node][0] + a.travel_cost))

    return calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination)


def find_optimal_strategy_improved(all_links, all_stops, destination, T=60.0):
    """
    Улучшенная модифицированная версия Spiess-Florian: максимизация вероятности прибытия вовремя (reliability).
    Теперь учитывает внутри-маршрутные перемещения: при движении по одному и тому же маршруту
    не добавляется время ожидания, в отличие от пересадок между маршрутами.
    
    mean_var[i] = (mean_time, variance_time) — параметры нормального распределения
                  оставшегося времени от узла i до destination.
    R_i = P(оставшееся время ≤ T) = norm.cdf(T - mean, scale=sqrt(variance))
    """
    if VERBOSE:
        print("Initialization for arrive time model")
    
    # Для каждой остановки будем хранить параметры (mean, variance) для каждого маршрута
    mean_var = {}
    freqs = {}
    for stop in all_stops:
        mean_var[stop] = {}
        freqs[stop] = {}

    # Устанавливаем конечную точку
    mean_var[destination] = {None: (0.0, 0.0)}  # специальное значение для конечной точки
    freqs[destination] = {None: 0.0}
    
    attractive_set = []
    
    # Группируем связи по конечной остановке
    incoming_links = {}
    for link in all_links:
        incoming_links.setdefault(link.to_node, []).append(link)
    
    # Инициализируем приоритетную очередь
    pq = PriorityQueue2()
    
    # Инициализируем связи, ведущие к destination
    if destination in incoming_links:
        for link in incoming_links[destination]:
            i = link.from_node
            j = link.to_node  # destination
            route_id = link.route_id
            
            # Находим параметры из конечной точки
            mean_dest, var_dest = mean_var[j].get(None, (0.0, 0.0))
            
            # Определяем, нужно ли добавлять время ожидания
            # Если это продолжение того же маршрута, время ожидания не добавляется
            freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
            mean_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
            var_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
            
            # При перемещении по одному маршруту не добавляем время ожидания
            tent_mean = link.travel_cost + mean_dest  # без ожидания
            tent_var = var_dest  # без дополнительной дисперсии ожидания
            
            tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(max(tent_var, 1e-8)))
            
            pq.push(link, -tent_r, tent_mean)
    
    while True:
        entry = pq.pop()
        if entry[0] is None:
            break
        link, priority, orig_priority = entry
        current_priority_r = -priority
        mean_travel_time_priority = orig_priority
        
        i = link.from_node  # текущая остановка
        j = link.to_node    # следующая остановка
        route_id = link.route_id  # маршрут, которым мы едем
        
        if i not in all_stops or j not in all_stops:
            continue
        
        # Находим параметры для маршрута route_id в узле j
        mean_j, var_j = None, None
        if j in mean_var and route_id in mean_var[j]:
            mean_j, var_j = mean_var[j][route_id]
        elif j in mean_var and mean_var[j]:  # если для конкретного маршрута нет данных, берем минимальные
            # берем первый доступный набор параметров
            first_route = next(iter(mean_var[j]))
            mean_j, var_j = mean_var[j][first_route]
        elif j == destination:
            mean_j, var_j = 0.0, 0.0
        else:
            continue  # невозможно добраться до цели из узла j
        
        if mean_j is None or var_j is None:
            continue
        
        # Рассчитываем параметры через эту связь
        # При перемещении по одному и тому же маршруту не добавляем время ожидания
        mean_via_link = link.travel_cost + mean_j
        var_via_link = var_j  # дисперсия не увеличивается при внутри-маршрутном перемещении
        
        # Проверяем, улучшит ли это наше значение для узла i на маршруте route_id
        current_mean, current_var = mean_var[i].get(route_id, (math.inf, 0.0))
        current_r = stats.norm.cdf(T - current_mean, scale=math.sqrt(max(current_var, 1e-8)))
        
        # Рассчитываем новую вероятность
        new_r = stats.norm.cdf(T - mean_via_link, scale=math.sqrt(max(var_via_link, 1e-8)))
        
        if VERBOSE:
            print(f"Process: a = ({i}, {j}) via route {route_id}")
            print(f"  mean_via_link = {mean_via_link}, var_via_link = {var_via_link}")
            print(f"  new_r = {new_r}, current_r = {current_r}")
        
        # Проверяем, улучшает ли это наше состояние
        if new_r > current_r + 1e-6 or (abs(new_r - current_r) <= EPSILON and mean_via_link < current_mean):
            # Обновляем параметры для маршрута route_id в узле i
            if i not in mean_var:
                mean_var[i] = {}
                freqs[i] = {}
            
            mean_var[i][route_id] = (mean_via_link, var_via_link)
            
            # Обновляем частоту для этого маршрута
            freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
            freqs[i][route_id] = freq
            
            if VERBOSE:
                print(f"Updated node {i} for route {route_id}: R = {new_r:.4f}, mean = {mean_via_link:.2f}, var = {var_via_link:.2f}")
            
            # Добавляем связь в привлекательное множество
            attractive_set.append(link)
            
            # Обновляем приоритеты для связей, входящих в узел i
            if i in incoming_links:
                for prev_link in incoming_links[i]:
                    prev_route = prev_link.route_id
                    # Рассчитываем параметры для связи prev_link
                    prev_mean, prev_var = mean_var[i].get(prev_route, (math.inf, 0.0))
                    
                    if math.isinf(prev_mean):
                        continue  # Нет пути из узла prev_link.from_node через prev_link.to_node
                    
                    # При пересадке с маршрута prev_route на route_id может потребоваться ожидание
                    prev_freq = INFINITE_FREQUENCY if prev_link.headway <= 0 else 1.0 / prev_link.headway
                    prev_mean_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                    prev_tent_mean = prev_mean_wait + prev_link.travel_cost + prev_mean
                    
                    prev_var_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                    prev_tent_var = prev_var_wait + prev_var
                    
                    prev_tent_var = max(prev_tent_var, 1e-8)
                    prev_tent_r = stats.norm.cdf(T - prev_tent_mean, scale=math.sqrt(prev_tent_var))
                    
                    pq.update(prev_link, -prev_tent_r, prev_tent_mean)
        
        # Также проверяем возможность пересадки - когда пассажир прибывает в узел i на одном маршруте
        # и может пересесть на маршрут link.route_id
        for prev_route in mean_var[j]:
            if prev_route != route_id and prev_route is not None:
                # Есть возможность пересесть с маршрута prev_route на route_id в узле i
                mean_on_prev_route, var_on_prev_route = mean_var[j][prev_route]
                
                # При пересадке нужно учитывать время ожидания
                wait_time = link.headway / 2.0 if link.headway > 0 else 0  # среднее время ожидания
                var_wait = link.headway / 4.0 if link.headway > 0 else 0  # дисперсия для равномерного распределения
                
                total_mean_if_transfer = wait_time + link.travel_cost + mean_on_prev_route
                total_var_if_transfer = var_wait + var_on_prev_route
                
                transfer_r = stats.norm.cdf(T - total_mean_if_transfer, scale=math.sqrt(max(total_var_if_transfer, 1e-8)))
                
                current_mean, current_var = mean_var[i].get(route_id, (math.inf, 0.0))
                current_r = stats.norm.cdf(T - current_mean, scale=math.sqrt(max(current_var, 1e-8)))
                
                if transfer_r > current_r + 1e-6 or (abs(transfer_r - current_r) <= EPSILON and total_mean_if_transfer < current_mean):
                    if i not in mean_var:
                        mean_var[i] = {}
                        freqs[i] = {}
                    
                    mean_var[i][route_id] = (total_mean_if_transfer, total_var_if_transfer)
                    
                    freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
                    freqs[i][route_id] = freq
                    
                    if VERBOSE:
                        print(f"Transfer improvement: from route {prev_route} to {route_id} at node {i}")
                    
                    # Обновляем приоритеты для связей, входящих в узел i
                    if i in incoming_links:
                        for prev_link in incoming_links[i]:
                            prev_mean, prev_var = mean_var[i].get(prev_route, (math.inf, 0.0))
                            
                            if math.isinf(prev_mean):
                                continue
                            
                            prev_freq = INFINITE_FREQUENCY if prev_link.headway <= 0 else 1.0 / prev_link.headway
                            prev_mean_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                            prev_tent_mean = prev_mean_wait + prev_link.travel_cost + prev_mean
                            
                            prev_var_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                            prev_tent_var = prev_var_wait + prev_var
                            
                            prev_tent_var = max(prev_tent_var, 1e-8)
                            prev_tent_r = stats.norm.cdf(T - prev_tent_mean, scale=math.sqrt(prev_tent_var))
                            
                            pq.update(prev_link, -prev_tent_r, prev_tent_mean)

    # Преобразуем результат в старый формат для совместимости
    # Берем параметры с наибольшей вероятностью прибытия вовремя для каждой остановки
    final_mean_var = {}
    final_freqs = {}
    for stop in all_stops:
        if stop in mean_var and mean_var[stop]:
            best_params = None
            best_r = -1.0
            
            for route_params in mean_var[stop].values():
                mean_val, var_val = route_params
                r = stats.norm.cdf(T - mean_val, scale=math.sqrt(max(var_val, 1e-8)))
                if r > best_r:
                    best_r = r
                    best_params = route_params
            
            if best_params:
                final_mean_var[stop] = best_params
                # Суммируем частоты по всем маршрутам
                final_freqs[stop] = sum(freqs[stop].values()) if stop in freqs else 0.0
            else:
                final_mean_var[stop] = (math.inf, 0.0)
                final_freqs[stop] = 0.0
        else:
            final_mean_var[stop] = (math.inf, 0.0)
            final_freqs[stop] = 0.0
    
    return Strategy(final_mean_var, final_freqs, attractive_set)


def compute_sf_improved(all_links, all_stops, destination, od_matrix, T=60):
    ops = find_optimal_strategy_improved(all_links, all_stops, destination, T)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)


def compute_sf(all_links, all_stops, destination, od_matrix, T=60):
    ops = find_optimal_strategy(all_links, all_stops, destination, T)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def parse_gtfs(directory, limit=10000):
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory)
    od_matrix = { "100457-8017": { "100457-1002179": 1000 } }
    destination = "100457-1002179"
    result = compute_sf(all_links, all_stops, destination, od_matrix)