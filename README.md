# Dashboards

A collection of business intelligence dashboards built with Python and Streamlit.

Each dashboard lives in its own folder with its own data, analysis and documentation, and runs
independently of the others. Every project is self-contained: it generates or loads its own data
locally, performs its own analysis, and requires no cloud services or API keys.

## Projects

| Project | Description |
| --- | --- |
| [Naeem Sports Dashboard](./Naeem%20Sports%20Dashboard) | Shop intelligence for Naeem Sports Goods Shop |
| [Sadat Surgical Dashboard](./Sadat%20Surgical%20Dashboard) | Inventory intelligence for Sadat Surgical and Medical Supplies |

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
streamlit run dashboard/app.py
```
