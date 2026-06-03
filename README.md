# Garmin Health Insights

MVP aplikacji, która zamienia dane zdrowotne z Garmin Connect/Fenix 7X Pro Solar
na codzienny raport o stanie organizmu, gotowości treningowej i sugestiach na
dany dzień.

Obecna wersja działa bez przechowywania loginu i hasła do Garmina: wczytuje
lokalny eksport JSON/CSV z Garmin Connect albo plik przygotowany przez przyszły
adapter API. Dzięki temu można bezpiecznie rozwijać analizę danych, a automatyczne
pobieranie podpiąć jako osobny moduł.

## Co aplikacja analizuje

- sen (`sleep_score` albo `sleep_hours`),
- HRV,
- tętno spoczynkowe,
- Body Battery,
- średni stres,
- czas regeneracji,
- obciążenie treningowe,
- dodatkowe pola, takie jak kroki, kalorie, SpO2 i VO2max.

Na tej podstawie generuje:

- wynik gotowości 0-100,
- etykietę gotowości: `wysoka`, `umiarkowana`, `niska`,
- najważniejsze sygnały względem osobistej normy,
- praktyczne sugestie treningowe/regeneracyjne.

## Uruchomienie

Wymagany jest Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Przykładowy raport:

```bash
garmin-health-insights report \
  --input sample_data/daily_health_sample.json \
  --date 2026-06-03
```

Raport w JSON:

```bash
garmin-health-insights report \
  --input sample_data/daily_health_sample.json \
  --format json
```

Bez instalacji pakietu można użyć:

```bash
PYTHONPATH=src python -m garmin_health_insights report \
  --input sample_data/daily_health_sample.json
```

## Format danych wejściowych

Obsługiwany jest JSON jako lista rekordów:

```json
[
  {
    "date": "2026-06-03",
    "resting_hr": 57,
    "hrv_ms": 51,
    "sleep_score": 66,
    "sleep_hours": 6.2,
    "body_battery": 48,
    "stress_score": 61,
    "training_load": 520,
    "recovery_hours": 42
  }
]
```

Można też użyć obiektu z polem `days`, `data`, `records` albo `dailyMetrics`.
CSV powinien mieć nagłówki zgodne z powyższymi polami.

Importer akceptuje również część nazw spotykanych w eksporcie Garmin, np.
`sleepScore`, `restingHeartRate`, `bodyBattery`, `avgStressLevel`,
`trainingLoad` i `recoveryTimeHours`.

## Docelowe pobieranie danych z Garmina

Garmin nie udostępnia swobodnego publicznego API dla prywatnych aplikacji.
Najbezpieczniejsza ścieżka produkcyjna to:

1. oficjalny Garmin Health API, jeśli projekt spełnia wymagania dostępu,
2. albo lokalny/importowany eksport Garmin Connect bez przechowywania hasła,
3. później opcjonalny adapter synchronizacji, który zapisuje te same dzienne
   rekordy używane przez ten silnik.

Szczegóły integracji są opisane w `docs/garmin_integration.md`.

## Testy

```bash
PYTHONPATH=src python -m unittest
```
