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
python3 -m venv .venv
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
PYTHONPATH=src python3 -m garmin_health_insights report \
  --input sample_data/daily_health_sample.json
```

## Gdzie widzisz dane

Masz dwa widoki:

1. **Frontend w przeglądarce** - lokalny panel do wgrania pliku i zobaczenia raportu:

   ```bash
   PYTHONPATH=src python3 -m garmin_health_insights serve --port 8000
   ```

   Następnie otwórz `http://127.0.0.1:8000`. W Cursor Cloud użyj podglądu/forwardingu
   portu 8000. Na ekranie możesz wgrać JSON z Garmin Connect albo kliknąć raport demo.

2. **Terminal/automatyzacja** - komenda CLI generująca Markdown lub JSON:

   ```bash
   PYTHONPATH=src python3 -m garmin_health_insights report \
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

## Jak wpiąć zegarek

Fenix 7X Pro Solar nie powinien być integrowany bezpośrednio z tą aplikacją przez
Bluetooth/USB. Praktyczny przepływ danych wygląda tak:

1. zegarek synchronizuje zdrowie, sen i treningi do aplikacji Garmin Connect,
2. Garmin Connect zapisuje dane w chmurze Garmina,
3. ta aplikacja pobiera dane z eksportu JSON/CSV albo docelowo z Garmin Health API,
4. frontend wyświetla raport i sugestie.

W MVP importujesz plik ręcznie. W wersji produkcyjnej trzeba dodać adapter
`GarminHealthApiSource`, skonfigurować oficjalny dostęp Garmin Health API i
zapisywać dzienne rekordy w lokalnym magazynie.

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
PYTHONPATH=src python3 -m unittest discover -s tests
```
