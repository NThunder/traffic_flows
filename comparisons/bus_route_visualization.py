from matplotlib import pyplot as plt
import numpy as np
from utils import find_shortest_route_pair

def find_shortest_bus_route(original_links, all_stops):
    origin, destination = find_shortest_route_pair(original_links, max_stops=10)
    if origin is None or destination is None:
        stops_list = list(all_stops)
        if len(stops_list) < 2:
            print("Недостаточно остановок для тестирования")
            return None, None
        destination = stops_list[0]
        origin = stops_list[1] if len(stops_list) > 1 else stops_list[0]
    else:
        print(f"Найдена пара с маршрутом длиной до 10 остановок: {origin} -> {destination}")
    return origin, destination

def find_bus_route(bus_route_name, active_trips, stop_times, all_stops, route_names, all_links):
    # Параметры для тестирования
    # Найдем маршрут C962 и используем его остановки
    # Ищем маршрут по названию, а не по ID
    c962_route_id = None
    for route_id, route_name in route_names.items():
        if bus_route_name in route_name.lower():
            c962_route_id = route_id
            print(f"Найден маршрут C962 с ID: {c962_route_id}, название: {route_name}")
            break
    
    c962_stops = []
    if c962_route_id:
        for link in all_links:
            if link.route_id == c962_route_id:  # Ищем связи, принадлежащие найденному маршруту C962
                if link.from_node not in c962_stops:
                    c962_stops.append(link.from_node)
                if link.to_node not in c962_stops:
                    c962_stops.append(link.to_node)
    
    # Если маршрут C962 найден, используем его первую и последнюю остановку
    if c962_stops:
        # Сортируем остановки по порядку следования в маршруте
        # Для этого нужно построить путь
        c962_trip_ids = []
        for trip_id, route_id in active_trips.items():
            if route_id == c962_route_id:
                c962_trip_ids.append(trip_id)
        
        if c962_trip_ids:
            # Берем первую поездку маршрута C962 и получаем остановки в правильном порядке
            first_trip = c962_trip_ids[0]
            if first_trip in stop_times:
                trip_stops = stop_times[first_trip]
                # Сортируем по stop_sequence
                trip_stops.sort(key=lambda x: int(x['stop_sequence']))
                ordered_c962_stops = [stop['stop_id'] for stop in trip_stops]
                
                if len(ordered_c962_stops) >= 2:
                    origin = ordered_c962_stops[0]
                    destination = ordered_c962_stops[-1]
                    print(f"Используем маршрут C962: {origin} -> {destination}")

                    return origin, destination
                else:
                    # Если в маршруте менее 2 остановок, используем стандартную логику
                    pass
            else:
                # Если не найдена поездка C962, используем стандартную логику
                pass
        else:
            # Если не найдена поездка C962, используем стандартную логику
            pass
    else:
        # Если маршрут C962 не найден, используем стандартную логику
        pass

    origin, destination = find_shortest_bus_route(all_links, all_stops)
    return origin, destination

def get_stops_to_show(all_path_stops, path_stops_original, path_stops_prob, original_result, prob_result, origin, destination):
    # Если объединенный маршрут слишком длинный, используем более короткий
    if len(all_path_stops) > 10:
        if len(path_stops_original) <= len(path_stops_prob) and len(path_stops_original) <= 10:
            stops_to_show = path_stops_original
        elif len(path_stops_prob) <= 10:
            stops_to_show = path_stops_prob
        else:
            # Если оба маршрута длиннее 10, используем активные остановки, но ограничиваем до 10
            active_stops = set()
            for stop, volume in original_result.volumes.nodes.items():
                if volume != 0:
                    active_stops.add(stop)
            for stop, volume in prob_result.volumes.nodes.items():
                if volume != 0:
                    active_stops.add(stop)
            
            # Включаем origin и destination
            displayed_stops = [origin]
            if destination != origin and len(displayed_stops) < 10:
                displayed_stops.append(destination)
            
            # Добавляем остальные активные остановки
            for stop in active_stops:
                if stop != origin and stop != destination and len(displayed_stops) < 10:
                    displayed_stops.append(stop)
            
            stops_to_show = displayed_stops
    else:
        # Используем объединенный маршрут, но сохраняя логический порядок
        # Приоритет у оригинального маршрута
        stops_to_show = []
        added_stops = set()
        
        # Сначала добавляем остановки из оригинального маршрута
        for stop in path_stops_original:
            if stop not in added_stops and len(stops_to_show) < 10:
                stops_to_show.append(stop)
                added_stops.add(stop)
        
        # Потом добавляем оставшиеся из вероятностного маршрута
        for stop in path_stops_prob:
            if stop not in added_stops and len(stops_to_show) < 10:
                stops_to_show.append(stop)
                added_stops.add(stop)

    return stops_to_show

def create_bus_route_visualization(original_result, prob_result, all_stops, origin, destination, stop_names=None, route_names=None):
    """
    Создает визуализацию сравнения двух алгоритмов - только объемы
    """
    # Для более короткого маршрута, попробуем найти маршрут с меньшим количеством остановок
    # Используем стратегию для определения остановок на маршруте
    from collections import defaultdict
    
    # Построим список остановок в порядке следования из origin в destination
    # Используем a_set (множество рёбер оптимальной стратегии) для построения маршрута
    def get_path_stops(strategy, origin, destination):
        # Построим граф из рёбер в a_set
        graph = defaultdict(list)
        for link in strategy.a_set:
            graph[link.from_node].append((link.to_node, link))
        
        # Найдем путь от origin до destination с помощью BFS для получения кратчайшего пути
        from collections import deque
        queue = deque([(origin, [origin])])
        visited = {origin}
        
        while queue:
            current, path = queue.popleft()
            
            if current == destination:
                return path
            
            for next_node, link in graph[current]:
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append((next_node, path + [next_node]))
        
        return [origin, destination] # В крайнем случае, просто origin и destination
    
    # Для построения маршрута используем стратегию, у которой больше остановок на пути или обе стратегии
    path_stops_original = get_path_stops(original_result.strategy, origin, destination)
    
    # Объединяем остановки из обоих маршрутов, сохраняя порядок
    all_path_stops = set()
    all_path_stops.update(path_stops_original)
    
    # stops_to_show = get_stops_to_show(all_path_stops, path_stops_original, path_stops_prob, original_result, prob_result, origin, destination)
    # show just original
    stops_to_show = path_stops_original

    # Преобразуем ID остановок в их названия, если доступны
    if stop_names:
        stop_labels = [stop_names.get(stop, stop) for stop in stops_to_show]
    else:
        stop_labels = stops_to_show
    
    # Определяем, какие остановки являются origin или destination
    special_stops = []
    for stop in stops_to_show:
        if stop == origin and stop == destination:
            special_stops.append("origin & dest")
        elif stop == origin:
            special_stops.append("origin")
        elif stop == destination:
            special_stops.append("destination")
        else:
            special_stops.append("regular")
    
    # Создаем график - только сравнение объемов
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    
    # Получаем информацию о маршрутах для заголовка
    # Ищем уникальные route_id, участвующие в пути, но только для остановок, которые отображаются
    routes_used = set()
    
    for link in original_result.strategy.a_set:
        if link.from_node in stops_to_show and link.to_node in stops_to_show:
            routes_used.add(link.route_id)
            break
    
    # Преобразуем route_id в русские названия маршрутов, если доступны
    if route_names:
        route_labels = [route_names.get(route_id, route_id) for route_id in routes_used]
        routes_str = ", ".join(route_labels[:5])  # Ограничиваем до 5 маршрутов в заголовке
        if len(route_labels) > 5:
            routes_str += f" и еще {len(route_labels) - 5} маршрутов"
    else:
        routes_str = ", ".join(list(routes_used)[:5])  # Ограничиваем до 5 маршрутов в заголовке
        if len(routes_used) > 5:
            routes_str += f" и еще {len(routes_used) - 5} маршрутов"
    
    # Сравнение объемов на узлах
    x = np.arange(len(stops_to_show))
    width = 0.35
    
    # Получаем объемы для каждой остановки
    original_volumes = []
    for stop in stops_to_show:
        value = original_result.volumes.nodes.get(stop, 0)
        # Если значение - массив, берем первое значение
        if hasattr(value, '__len__') and not isinstance(value, str):
            original_volumes.append(value[0] if len(value) > 0 else 0)
        else:
            original_volumes.append(value)
    
    prob_volumes = []
    for stop in stops_to_show:
        value = prob_result.volumes.nodes.get(stop, 0)
        # Если значение - массив, берем первое значение
        if hasattr(value, '__len__') and not isinstance(value, str):
            prob_volumes.append(value[0] if len(value) > 0 else 0)
        else:
            prob_volumes.append(value)
    
    # Используем цвета для различия алгоритмов
    bars1 = ax.bar(x - width/2, original_volumes, width, label='Оригинальный алгоритм', alpha=0.8, color='skyblue')
    bars2 = ax.bar(x + width/2, prob_volumes, width, label='Алгоритм с учетом опоздания', alpha=0.8, color='orange')
    
    ax.set_xlabel('Остановки')
    ax.set_ylabel('Объемы')
    ax.set_title(f'Сравнение объемов на узлах (Маршруты: {routes_str})')
    ax.set_xticks(x)
    ax.set_xticklabels(stop_labels, rotation=45, ha="right")
    ax.legend()
    
    # Добавляем легенду для обозначения типов остановок
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='skyblue', label='Оригинальный алгоритм'),
                       Patch(facecolor='orange', label='Алгоритм с учетом опоздания')]
    
    # Также добавим информацию о том, какая остановка является начальной/конечной
    # Подписываем особым образом origin и destination
    for i, stop_type in enumerate(special_stops):
        if stop_type == "origin":
            ax.get_xticklabels()[i].set_weight('bold')
        elif stop_type == "destination":
            ax.get_xticklabels()[i].set_weight('bold')
        elif stop_type == "origin & dest":
            ax.get_xticklabels()[i].set_weight('bold')
            ax.get_xticklabels()[i].set_weight('bold')
    
    # fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=2)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])  # Делаем место для верхней легенды
    plt.savefig('gtfs_comparison_results.png', dpi=300, bbox_inches='tight')
    print(f"\nГрафик сравнения объемов сохранен в файл 'gtfs_comparison_results.png'")
    plt.show()