# Sadat Surgical and Medical Supplies — Inventory Intelligence Dashboard

A standalone, local inventory intelligence dashboard for **Sadat Surgical and Medical Supplies**.
It turns day-to-day sales and stock records into clear visual answers about what is selling, what is
in stock, what customers are likely to need next, and what deserves purchasing attention.

The project is entirely self-contained. It generates its own business data, performs its own
analysis and forecasting, and runs on a single computer with no internet connection, no cloud
services, and no API keys.

## Purpose

A growing surgical and medical supplies business carries many products with very different demand
patterns. Consumables such as gloves and face masks move in large volumes every week, while
specialist instruments sell slowly and steadily. Judging replenishment by eye across a catalogue
like that is difficult, and the cost of getting it wrong is either money tied up in shelves or a
customer who cannot be served.

This dashboard answers six business questions:

| Question | Where it is answered |
| --- | --- |
| How is my business doing? | Inventory Overview |
| What are customers buying? | Sales & Demand |
| What might customers need next? | 7-Day Demand Forecast |
| What should I pay attention to? | Needs Attention |
| What should I consider purchasing? | Reorder Recommendations |
| What is the whole picture? | Business Story |

## Features

- **Inventory overview** — headline figures for total products, stock availability, low stock,
  out-of-stock items, recent sales and expected demand, with an inventory health breakdown.
- **Sales analysis** — daily, weekly and monthly sales trends, category comparison, and the
  weekday pattern showing when customers usually buy.
- **Product performance** — best-selling and slow-moving products, plus a full profile for any
  individual product.
- **Demand forecasting** — a genuine seven-day expected demand figure for every product, learned
  from its own sales history.
- **Inventory alerts** — every product classified as Healthy, Attention, Critical or Out of Stock
  by comparing stock on hand with the demand expected over the coming week.
- **Reorder recommendations** — a prioritised, plain-language action list.
- **Business insights** — short written observations generated from the current data, never
  hard-coded, updating as filters change.

## Technology

Python, Streamlit, Pandas, NumPy, Plotly, Scikit-learn and SQLite. Nothing else is required.

## Project structure

```text
sadat-surgical-inventory-dashboard/
├── data/
│   ├── make_dataset.py        business data generation
│   └── sadat_surgical.db      created by the step above
├── dashboard/
│   ├── app.py                 Streamlit interface
│   ├── data_loader.py         data access and cleaning
│   ├── analytics.py           sales and inventory calculations
│   ├── forecasting.py         demand forecasting
│   ├── business_logic.py      inventory status and recommendations
│   ├── insights.py            written business observations
│   └── charts.py              visualisations
├── tests/
├── requirements.txt
└── README.md
```

## Local setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows: `.venv\Scripts\activate` — on macOS or Linux: `source .venv/bin/activate`

Install the dependencies:

```bash
pip install -r requirements.txt
```

Prepare the business data (run once):

```bash
python data/make_dataset.py
```

Start the dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard opens in a browser at `http://localhost:8501`. If the data has not been prepared yet,
the dashboard says so and shows the command to run — it never invents data to fill the gap.

Run the tests:

```bash
python -m pytest
```

## How the numbers are produced

The generated dataset covers two years of daily activity for 21 products across Surgical
Instruments and Medical Supplies. Each product has its own demand level, day-of-week pattern,
seasonal shape, long-term trend, occasional promotions and demand spikes. Stock is simulated day by
day: sales draw stock down, replenishment arrives after a delay, and products with thin cover
naturally run low or run out. A fixed random seed makes every run reproducible.

The seven-day forecast is learned from that history. For each product the forecast considers its
recent daily sales, the same weekday a week and two weeks earlier, its short and longer-term
average, the day of week, the month, promotion periods, and which product and category it belongs
to. Each of the seven days is forecast in turn, so a quiet weekend and a busy Monday come through as
different numbers rather than one figure repeated.

Inventory status compares stock on hand with the demand expected over those seven days. Stock
comfortably above expected demand is Healthy, stock close to it needs Attention, stock well below it
is Critical, and no stock at all is Out of Stock.

## Client demonstration

1. Open **Inventory Overview** — the headline numbers give the state of the business at a glance.
2. Point out **Inventory Health** and read the interpretation below the chart.
3. Move to **Sales Trend** and switch between Daily, Weekly and Monthly.
4. Show **Best-Selling Products** and the products that need attention.
5. Open **7-Day Demand Forecast** and select a product such as Face Masks.
6. Show how expected demand is separated from the sales history at today's line.
7. Open **Needs Attention** — the urgent products appear first.
8. Open **Reorder Recommendations** — a single list of what to act on.
9. Finish on **Business Story** and read the five sections aloud; they are written from the same
   data shown on every other page.

## Limitations

- The data in this dashboard is **synthetic**. It was generated to demonstrate the system and does
  not describe real trading history.
- This is a **demonstration system**, not a live inventory management platform.
- Forecasts are **estimates**. They describe what is likely, not what is certain.
- Historical sales can **understate true demand during a stockout**, because sales that could not be
  fulfilled were never recorded.
- Supplier lead times, prices, minimum order quantities and purchasing costs are **not modelled**,
  so the dashboard recommends attention rather than an exact order quantity.
- The dashboard is **not integrated** with any real purchasing, accounting or stock system.
- **No patient data or medical records** are used anywhere in this project.
- This is a **business tool, not a clinical system**, and it must not be used for clinical
  decisions.
