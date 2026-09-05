# Dashboards

A collection of business intelligence dashboards built with Python and Streamlit.

Each dashboard lives in its own folder with its own data, analysis and documentation, and runs
independently of the others. Every project is self-contained: it generates or loads its own data
locally, performs its own analysis, and requires no cloud services or API keys.

## Projects

| Project | Description |
| --- | --- |
| [Hotel Revenue and Demand Intelligence](./Hotel%20Revenue%20and%20Demand%20Intelligence) | Revenue, demand and guest intelligence for Grand Horizon Hotel |
| [Naeem Sports Dashboard](./Naeem%20Sports%20Dashboard) | Shop intelligence for Naeem Sports Goods Shop |
| [Sadat Surgical Dashboard](./Sadat%20Surgical%20Dashboard) | Inventory intelligence for Sadat Surgical and Medical Supplies |

### Hotel Revenue and Demand Intelligence

A revenue and demand intelligence dashboard for a 120-room hotel. It turns two years of booking
records into plain answers for an owner or general manager: how the hotel is performing, where the
money comes from, which rooms earn their keep, who the valuable guests are, why reservations fall
away, and how full the hotel is likely to be over the coming fortnight.

Includes an executive overview with a written business story, revenue analysis by room category,
booking source and guest type, booking and lead time patterns, room category ranking on yield and
occupancy, guest segmentation into value groups, cancellation analysis across six dimensions, a
fourteen-night demand and revenue forecast with accuracy measured against held-out nights,
prioritised management recommendations, and a business questions page that answers common
questions and links to the detail.

Built with Python, Streamlit, Pandas, NumPy, Plotly, Scikit-learn and SQLite.

### Naeem Sports Dashboard

A shop intelligence dashboard for a sports goods retailer. It turns two years of daily sales and
stock movements into plain answers for a shop owner: what is selling, which sports are driving the
business, what is running low, what may sell over the coming week, and what is worth reordering.

Includes a shop overview with a written daily story, sales momentum, category and product
rankings, product momentum and slow movers, inventory health classification, stock alerts, a
seven-day demand forecast for every product, weekly and seasonal demand patterns, and a
prioritised shopping list.

Built with Python, Streamlit, Pandas, NumPy, Plotly, Scikit-learn and SQLite.

### Sadat Surgical Dashboard

An inventory intelligence dashboard for a surgical and medical supplies business. It turns daily
sales and stock records into clear answers about what is selling, what is in stock, what customers
are likely to need over the next seven days, and which products need purchasing attention.

Includes sales trend analysis, category and product performance, a seven-day demand forecast for
every product, inventory health classification, reorder recommendations, and written business
insights generated from the data.

Built with Python, Streamlit, Pandas, NumPy, Plotly, Scikit-learn and SQLite.

## Running a dashboard

Each project folder contains its own README with setup instructions. In general:

```bash
cd "<project folder>"
pip install -r requirements.txt
python data/make_dataset.py
streamlit run app.py
```

The entry point differs between projects: the earlier dashboards run `dashboard/app.py`. Each
project README states which to use, along with how to run its tests.
