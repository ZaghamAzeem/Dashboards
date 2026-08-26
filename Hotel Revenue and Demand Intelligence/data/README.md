# Dataset

The dashboard runs on a synthetic dataset for a fictional property, **Grand Horizon Hotel**.
No real hotel records, guest identities, or third-party data are used anywhere in this project.

## Generating the data

```bash
python data/make_dataset.py
```

The script rebuilds `data/hotel.db` from scratch and prints a validation summary covering row
counts, the date range, occupancy and rate levels, duplicate identifiers, missing values, and
the distribution of bookings across room categories and channels.

Generation is deterministic: a fixed random seed produces byte-identical output on every run, so
results shown in the dashboard are reproducible. The database is not committed to the repository
because it is a binary artefact that can be rebuilt in a few seconds.

## What is simulated

The generator simulates a 120-room hotel night by night over two years, ending 31 August 2026.
For each stay date and room category it draws arrivals from a demand curve built from:

- **Seasonality** — a summer peak, a secondary winter peak, and a January/February trough
- **Weekly rhythm** — business demand concentrated midweek, leisure and couples at weekends
- **Named periods** — recurring fictional events such as the Harbour Lights Festival and the
  Spring Business Convention, each with its own demand profile
- **Promotions** — discounted periods that lift volume while lowering the achieved rate
- **A growth trend** — steady expansion that eases in the most recent months

Each arrival is assigned a length of stay, guest type, booking channel, region, party size, lead
time, nightly rate and cancellation outcome. Room inventory is tracked per category and per night,
so occupancy can never exceed the rooms that exist, and sell-outs occur naturally at peak times.

Rates respond to season, day of week, channel, length of stay, promotions and how full the hotel
already is. Cancellation probability responds to channel, guest type, lead time, promotional
status and whether the guest has stayed before — which is what makes the cancellation analysis in
the dashboard meaningful rather than decorative.

The first 45 simulated days are a warm-up period that fills the hotel before the reporting window
opens, so the series has no artificial ramp at the start.

## Tables

| Table | Grain | Purpose |
| --- | --- | --- |
| `bookings` | One row per reservation | Every reservation made, confirmed or cancelled, with rate, stay dates, channel, guest type and cancellation outcome |
| `rooms` | One row per room category | Inventory, capacity, published rate and description for each category |
| `guests` | One row per guest | Anonymised guest identifiers with stay counts, spending, preferences and cancellation behaviour |
| `daily_metrics` | One row per night | Rooms sold, occupancy, room revenue, average rate, RevPAR, arrivals, departures and period flags |

Guests are identified only by a sequential code such as `GUEST-00042`. No names, contact details,
addresses or any other personal information are generated or stored.

`daily_metrics` reconciles exactly with `bookings`: exploding every confirmed reservation into its
individual room nights reproduces the rooms sold and room revenue for each night. The test suite
checks this on every run.

## Regenerating after changes

Editing the constants at the top of `make_dataset.py` — room mix, seasonality, channel behaviour,
cancellation rates — and rerunning the script rebuilds the whole database. The dashboard reads
whatever it finds, so no other file needs to change.
