# 🏆 Naeem Sports Goods Shop — Shop Intelligence Dashboard

**Know what is selling. Know what is needed.**

An interactive business dashboard that turns two years of sports retail sales and
inventory data into plain-language answers for a shop owner: what is selling, what
customers like, what is running low, and what is worth reordering this week.

The dashboard is built for someone who does not use computers much. Every chart
answers one business question, every number is followed by a sentence explaining
what it means, and nothing technical is shown on screen.

---

## Project Overview

Small sports retailers usually know their shop by feel. They know the busy days and
the popular products, but the detail sits in a drawer of receipts. This project takes
the same information a till would capture — daily sales and stock movements — and
turns it into a picture the owner can read in a minute.

The dashboard covers six views:

| Page | Question it answers |
| --- | --- |
| 🏠 Shop Home | How is my shop doing right now? |
| 📊 Sales Story | Which sports and days are driving sales? |
| 🏆 Customers' Favourites | What are people actually buying? |
| 📦 Stock Room | What do I have, and what is running out? |
| 🔮 What May Sell Next | What might customers buy in the coming week? |
| 🛒 Shopping List | What should I think about restocking? |

---

## Business Problem

A sports shop carries products across several sports, each with its own season.
Cricket picks up in spring and summer, badminton in winter, fitness in January.
Without a clear view of demand, a shop tends to:

- **run out of best sellers** at exactly the moment customers want them
- **miss sales** that quietly go to the shop down the road
- **tie up cash** in products that sit on the shelf for months
- **overlook slow movers** that take up space without earning it
- **struggle to spot trends** until a season has already passed

The demonstration dataset shows this happening: several of the shop's strongest
sellers are sitting at zero stock while demand for them is still climbing. That is
the story the dashboard is built to surface.

---

## Features

- **Shop overview** — a snapshot of sales, the current favourite, stock alerts, and
  expected demand for the coming week
- **Today's Story** — three plain-language sentences generated from the live data
- **Sales momentum** — whether sales are picking up, stable, or slowing, with the
  comparison against the previous period drawn on the chart
- **Sales analytics** — daily, weekly, and monthly views of money taken
- **Category performance** — every sport compared by sales, units, and share
- **Product rankings** — a best sellers podium and a top ten
- **Product momentum** — items selling faster now than they were four weeks ago
- **Slow movers** — the quietest products, flagged for monitoring rather than culling
- **Inventory health** — every product sorted into Good Stock, Running Low,
  Restock Needed, or Out of Stock
- **Stock alerts** — the products needing attention, most urgent first
- **Demand forecasting** — a seven-day demand estimate for every product
- **Shopping list** — a prioritised list of what to review for reordering
- **Smart insights** — six short observations drawn from the data
- **Weekly and seasonal patterns** — the busiest days and how sports move across the year

Every figure on screen is calculated from the generated dataset. Nothing is hard-coded.

---

## Technology

- **Python 3.11+**
- **Streamlit** — the dashboard itself
- **Pandas** and **NumPy** — data preparation and analytics
- **Plotly** — interactive charts
- **Scikit-learn** — gradient boosted demand forecasting
- **SQLite** — local storage, through the Python standard library

No API keys, no cloud services, no external calls. Once the dependencies are
installed and the dataset is generated, the dashboard runs entirely offline.

---

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Generate the local dataset (creates `data/sports_shop.db`):

```bash
python data/make_dataset.py
```

Run the dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard opens in a browser and goes straight to the Shop Home page. There is
no login.

---

## Running the Tests

```bash
python -m pytest tests -q
```

The suite covers the data generator, the analytics functions, the forecasting
model and its fallback, the business rules, the generated insight text, and chart
rendering.

---

## Client Demonstration

A natural order for showing the dashboard to a shop owner:

1. **Shop Home** — "This is the overall picture of the shop."
2. **Today's Story** — "The dashboard writes out the important things happening right now."
3. **Sales Story** — "Here we can see which sports and days drive the sales."
4. **Customers' Favourites** — "These are the products customers buy most."
5. **Stock Room** — "This shows which products have enough stock and which need attention."
6. **What May Sell Next** — "The system uses past sales patterns to estimate the coming week."
7. **Shopping List** — "And this turns all of it into a simple list worth reviewing."

A good product to open on the forecast page is one of the out-of-stock best sellers.
It shows strong sales history, a sharp drop to zero when the shelf emptied, and
demand that is still expected next week — the clearest example of a sale being lost.

---

## Project Structure

```text
Naeem Sports DashBoard/
│
├── data/
│   ├── make_dataset.py        synthetic data generator
│   └── sports_shop.db         generated SQLite database
│
├── dashboard/
│   ├── app.py                 Streamlit application and page layouts
│   ├── data_loader.py         database access, validation, caching
│   ├── analytics.py           sales, category, momentum and pattern calculations
│   ├── forecasting.py         seven-day demand model and fallback
│   ├── business_logic.py      stock status, priorities, wording rules
│   ├── insights.py            plain-language story generation
│   ├── charts.py              Plotly figures
│   └── ui.py                  styling and reusable card components
│
├── tests/
│   ├── conftest.py
│   ├── test_dataset.py
│   ├── test_analytics.py
│   ├── test_forecasting.py
│   ├── test_business_logic.py
│   ├── test_insights.py
│   └── test_charts.py
│
├── .streamlit/config.toml
├── requirements.txt
└── README.md
```

---

## How the Data Is Built

`data/make_dataset.py` simulates a two-year trading history for 45 products across
six sports. It is not random noise — the generator models the behaviour a real shop
would show:

- **Popularity tiers** so some products sell many times more than others
- **Weekly rhythm** with Saturday the strongest day and midweek the quietest
- **Seasonality per sport**, each with its own twelve-month shape
- **Long-term trends**, with some products growing and others fading
- **Promotions** that cut the price and lift demand for a few days
- **Tournament spikes** that briefly boost a whole sport
- **Inventory simulation** where sales draw stock down, replenishment tops it up,
  and under-ordering produces genuine stockouts

Sales are capped by the stock actually on the shelf, so a stockout suppresses
recorded sales exactly as it would in a real shop.

The generator uses a fixed random seed, so the same run on the same day produces
the same dataset. The two-year window ends on the day the script is run, which keeps
the demonstration current rather than anchored to a date in the past.

---

## How the Forecast Works

The dashboard estimates demand for the next seven days for every product. It learns
from the sales history using recent sales at several lags, rolling averages over one,
two and four weeks, the day of the week, the month, the price, and which product and
sport it belongs to. Predictions are made one day at a time and fed back in, so the
weekly rhythm carries through the whole seven days rather than repeating one number.

Forecasts are always non-negative, always finite, and capped against the product's own
history so an unusual week cannot produce an absurd number. A product without enough
history falls back to a seasonal average of its recent sales instead of failing.

For products currently out of stock, the forecast reflects the demand the shop is
likely to see rather than the zero sales it is recording — which is the number that
matters when deciding what to reorder.

---

## Limitations

This is a demonstration application. It is important to be clear about what it is not:

- The **dataset is entirely synthetic**. No real shop data is used.
- The **products are fictional**. No real brand or manufacturer data is included.
- **Forecasts are estimates**, not promises. They describe a likely pattern based on
  past sales and will be wrong sometimes.
- **Supplier lead times are not modelled.** The dashboard says a product is worth
  reviewing; it does not know how long delivery takes.
- **Exact purchase quantities are not calculated.** Deciding how much to order
  depends on supplier terms, budget, and storage, none of which are in the data.
- **Profit and margin are not included**, because cost prices are not part of the
  generated dataset. Every money figure is revenue, not profit.
- **No customer personal information** is generated, stored, or used anywhere.
- Money is shown in Pakistani Rupees, using lakh and crore for large amounts.

---

## Notes

The dashboard deliberately hides all technical detail from the user interface. There
are no model names, no database paths, no query text, and no error tracebacks on
screen. If the shop data cannot be loaded, the dashboard shows a short, friendly
message and a refresh button instead.
