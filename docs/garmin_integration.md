# Integracja z Garmin

## Założenie produktowe

Aplikacja ma codziennie zebrać dane zdrowotne z zegarka Garmin Fenix 7X Pro
Solar, przeliczyć je na stan organizmu i zaproponować decyzję treningową na
dany dzień.

Pierwszy etap repozytorium rozdziela dwie odpowiedzialności:

1. **źródło danych** - dostarcza dzienne metryki w postaci `DailyMetrics`,
2. **silnik insightów** - ocenia gotowość i generuje raport.

Dzięki temu można już testować jakość rekomendacji na eksporcie z Garmin Connect,
a automatyczne pobieranie dodać bez przepisywania analizy.

## Widok użytkownika

Frontend uruchamiasz lokalnie komendą:

```bash
PYTHONPATH=src python3 -m garmin_health_insights serve --port 8000
```

Panel działa pod `http://127.0.0.1:8000` i korzysta z endpointu `POST /api/report`.
Przeglądarka wysyła rekordy JSON do backendu, a backend zwraca gotowy raport
z tego samego silnika, którego używa CLI.

## Dostęp do danych Garmin

### Oficjalna ścieżka

Garmin Health API jest właściwym rozwiązaniem produkcyjnym, ale wymaga dostępu
udzielonego przez Garmin i konfiguracji aplikacji po stronie partnera. Adapter
API powinien mapować odpowiedzi na pola:

- `date`,
- `resting_hr`,
- `hrv_ms`,
- `sleep_score`,
- `sleep_hours`,
- `body_battery`,
- `stress_score`,
- `spo2`,
- `steps`,
- `calories`,
- `training_load`,
- `recovery_hours`,
- `vo2max`.

### Ścieżka lokalna / MVP

Do czasu uzyskania dostępu API aplikacja przyjmuje pliki JSON lub CSV. Taki plik
może pochodzić z eksportu Garmin Connect, narzędzia pośredniego albo ręcznie
przygotowanego procesu synchronizacji.

Przykład:

```bash
garmin-health-insights report --input sample_data/daily_health_sample.json
```

## Zakres kolejnych adapterów

Nowe źródło powinno implementować protokół `MetricsSource`:

```python
class MetricsSource(Protocol):
    def load(self) -> list[DailyMetrics]:
        ...
```

Proponowane adaptery:

1. `GarminHealthApiSource` - oficjalny endpoint Garmin Health API,
2. `GarminConnectExportSource` - bardziej szczegółowy parser pełnego eksportu
   Garmin Connect,
3. `LocalDailyStore` - lokalna baza SQLite z historią dziennych rekordów.

## Prywatność

Dane zdrowotne są wrażliwe. Produkcyjna aplikacja powinna:

- szyfrować lokalny magazyn,
- nie zapisywać hasła do Garmin Connect w plikach tekstowych,
- umożliwiać usunięcie danych,
- oddzielać tokeny dostępu od raportów,
- jasno oznaczać, że sugestie nie są diagnozą medyczną.
