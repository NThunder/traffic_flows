# traffic_flows

## Запуск
```bash
pip install -r requirements.txt
pip install -e .
python3 ./comparisons/compare_volumes.py --mode sample  --T 34
```
## Результат
![Сравнение](visual/network_volumes_highlightev2d.png )
**Примечание: модифицированный алгоритм выбирает Res3 --> DownTown, так как это увеличивает вероятность прийти вовремя с 0.34 до 0.41**


### Математичеcкое описание методов в description.ipynb


Проведены расчёты на [дорожной сети города Москвы](https://busmaps.com/en/russia/open-data-portal-moscow/moscow-official) состоящей из 10104 автобусных остановок и метро

```bash
python3 ./comparisons/compare_volumes.py --mode gtfs  --T 60 --limit 100000
```

```
destination=100457-17317
Найдено 745 остановок, из которых можно доехать до 100457-17317
    Сравнение распределений потоков (original vs modified):
        Средний объём на рёбрах:
            Original (только активные):  среднее = 15756.28, всего рёбер = 753
            Modified (только активные): среднее = 19913.91, всего рёбер = 746
```

***Выводы: средняя загруженность рёбер графа увеличилась***

## Запуск юнит-тестов

Для запуска всех юнит-тестов выполните:

```bash
python -m pytest unit_tests/ -v
```

Для запуска тестов только для определенного модуля:

```bash
python -m pytest unit_tests/test_florian.py -v
```

```bash
python -m pytest unit_tests/test_visualization.py -v
```
