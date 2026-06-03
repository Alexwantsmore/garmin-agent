# Garmin Health Insights

MVP aplikacji, która zamienia dane zdrowotne z Garmin Connect/Fenix 7X Pro Solar
na codzienny raport o stanie organizmu, gotowości treningowej i sugestiach na
dany dzień.

Obecna wersja potrafi działać na dwa sposoby: wczytać lokalny eksport JSON/CSV
albo zalogować się do konta Garmin Connect przez nieoficjalną bibliotekę
`garminconnect` i zapisać zsynchronizowane metryki do lokalnego pliku JSON.
Hasło nie jest zapisywane w repozytorium; biblioteka przechowuje tylko tokeny
sesji w lokalnym katalogu, domyślnie `~/.garminconnect`.

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

## Pobranie danych przez konto Garmin Connect

Jeśli nie masz dostępu do oficjalnego Garmin Health API, użyj synchronizacji
przez konto Garmin Connect:

```bash
export GARMIN_EMAIL="twoj-email@example.com"
export GARMIN_PASSWORD="twoje-haslo"
PYTHONPATH=src python3 -m garmin_health_insights sync --days 30 --output data/garmin_daily.json
```

Możesz też pominąć `GARMIN_PASSWORD` - wtedy aplikacja poprosi o hasło w
terminalu. Jeśli konto ma MFA/2FA, pojawi się prompt na kod. Przy pierwszym
logowaniu biblioteka zapisuje tokeny do `~/.garminconnect`, a kolejne
uruchomienia próbują użyć tokenów bez ponownego pytania o hasło.

Potem uruchom frontend i wgraj plik `data/garmin_daily.json`:

```bash
PYTHONPATH=src python3 -m garmin_health_insights serve --port 8000
```

Uwaga: to integracja nieoficjalna przez Garmin Connect. Garmin może zmienić
mechanizm logowania, wymusić ponowne MFA albo nałożyć limity zapytań.

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
3. komenda `sync` loguje się do konta Garmin Connect i pobiera ostatnie dni,
4. aplikacja zapisuje `data/garmin_daily.json`,
5. frontend wyświetla raport i sugestie po wgraniu tego pliku.

Czyli „wpięcie zegarka” odbywa się przez konto Garmin Connect, nie przez kabel
ani bezpośredni Bluetooth.

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
