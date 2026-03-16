#Sales Analytics Dashboard
#Interactive Dash app with synthetic multi-region, multi-category sales data.
#Demonstrates filtering, KPI cards, and 4 reactive chart types.

import numpy as np
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go


# Data generation — realistic synthetic sales data
def generate_sales_data():
    np.random.seed(42)
    regions = ['North', 'South', 'East', 'West']
    categories = ['Electronics', 'Clothing', 'Food', 'Furniture']
    dates = pd.date_range('2020-01-01', '2024-12-01', freq='MS')

    region_strength = {'North': 1.2, 'South': 0.9, 'East': 1.0, 'West': 1.1}
    category_base = {'Electronics': 12000, 'Clothing': 8000, 'Food': 15000, 'Furniture': 6000}
    price_range = {
        'Electronics': (40, 80),
        'Clothing': (20, 50),
        'Food': (5, 20),
        'Furniture': (60, 150)
    }

    records = []
    for region in regions:
        for category in categories:
            lo, hi = price_range[category]
            for date in dates:
                trend = category_base[category] * 0.04 * (date.year - 2020)
                seasonality = 1 + 0.25 * np.sin(2 * np.pi * (date.month - 9) / 12)
                holiday = 1.35 if date.month in [11, 12] else 1.0
                noise = 1 + np.random.normal(0, 0.08)

                revenue = (category_base[category]
                           * region_strength[region]
                           * seasonality * holiday * noise + trend)
                units = max(1, int(revenue / np.random.uniform(lo, hi)))

                records.append({
                    'Date': date,
                    'Year': date.year,
                    'Month': date.strftime('%b'),
                    'Region': region,
                    'Category': category,
                    'Revenue': round(max(0, revenue), 2),
                    'Units': units,
                })
    return pd.DataFrame(records)


df = generate_sales_data()
YEARS = sorted(df['Year'].unique())

# App
app = dash.Dash(__name__)
server = app.server
app.title = 'Sales Analytics Dashboard'

app.layout = html.Div([

    # Header
    html.Div([
        html.H1('Sales Analytics Dashboard'),
        html.P('Synthetic multi-region retail data (2020-2024). '
               'Filter by region, category, and year range.'),
    ], className='header'),

    # Filters
    html.Div([
        html.Div([
            html.Label('Region'),
            dcc.Dropdown(
                id='region-filter',
                options=[{'label': r, 'value': r} for r in sorted(df['Region'].unique())],
                value=list(df['Region'].unique()),
                multi=True, clearable=False,
            ),
        ], className='filter-item'),

        html.Div([
            html.Label('Category'),
            dcc.Dropdown(
                id='category-filter',
                options=[{'label': c, 'value': c} for c in sorted(df['Category'].unique())],
                value=list(df['Category'].unique()),
                multi=True, clearable=False,
            ),
        ], className='filter-item'),

        html.Div([
            html.Label('Year Range'),
            dcc.RangeSlider(
                id='year-slider',
                min=YEARS[0], max=YEARS[-1], step=1,
                marks={str(y): str(y) for y in YEARS},
                value=[YEARS[0], YEARS[-1]],
            ),
        ], className='filter-item slider'),
    ], className='filters'),

    # KPI cards
    html.Div(id='kpi-cards', className='kpi-row'),

    # Charts — row 1
    html.Div([
        html.Div([dcc.Graph(id='trend-line')], className='chart-half'),
        html.Div([dcc.Graph(id='category-bar')], className='chart-half'),
    ], className='chart-row'),

    # Charts — row 2
    html.Div([
        html.Div([dcc.Graph(id='region-pie')], className='chart-half'),
        html.Div([dcc.Graph(id='monthly-heatmap')], className='chart-half'),
    ], className='chart-row'),

], className='container')


# Callbacks
@app.callback(
    [Output('kpi-cards', 'children'),
     Output('trend-line', 'figure'),
     Output('category-bar', 'figure'),
     Output('region-pie', 'figure'),
     Output('monthly-heatmap', 'figure')],
    [Input('region-filter', 'value'),
     Input('category-filter', 'value'),
     Input('year-slider', 'value')]
)
def update_dashboard(regions, categories, year_range):
    filtered = df[
        (df['Region'].isin(regions)) &
        (df['Category'].isin(categories)) &
        (df['Year'] >= year_range[0]) &
        (df['Year'] <= year_range[1])
    ]

    # --- KPI cards ---
    total_rev = filtered['Revenue'].sum()
    total_units = filtered['Units'].sum()
    avg_rev_unit = total_rev / total_units if total_units else 0

    # YoY growth: compare last year in range vs previous
    last_yr = filtered[filtered['Year'] == year_range[1]]['Revenue'].sum()
    prev_yr = filtered[filtered['Year'] == year_range[1] - 1]['Revenue'].sum()
    yoy = ((last_yr - prev_yr) / prev_yr * 100) if prev_yr and prev_yr > 0 else 0

    kpis = [
        _kpi('Total Revenue', f'${total_rev:,.0f}'),
        _kpi('Total Units Sold', f'{total_units:,}'),
        _kpi('Avg Revenue / Unit', f'${avg_rev_unit:,.2f}'),
        _kpi('YoY Growth', f'{yoy:+.1f}%'),
    ]

    # --- Monthly Revenue Trend ---
    monthly = filtered.groupby('Date')['Revenue'].sum().reset_index()
    trend = px.area(monthly, x='Date', y='Revenue',
                    title='Monthly Revenue Trend',
                    labels={'Revenue': 'Revenue ($)', 'Date': ''})
    trend.update_layout(margin=dict(t=40, b=20))

    # --- Revenue by Category ---
    cat_rev = filtered.groupby('Category')['Revenue'].sum().reset_index()
    cat_rev = cat_rev.sort_values('Revenue', ascending=True)
    bar = px.bar(cat_rev, x='Revenue', y='Category', orientation='h',
                 title='Revenue by Category', color='Category',
                 labels={'Revenue': 'Revenue ($)', 'Category': ''})
    bar.update_layout(margin=dict(t=40, b=20), showlegend=False)

    # --- Regional Distribution ---
    reg_rev = filtered.groupby('Region')['Revenue'].sum().reset_index()
    pie = px.pie(reg_rev, values='Revenue', names='Region',
                 title='Revenue by Region', hole=0.4)
    pie.update_layout(margin=dict(t=40, b=20))

    # --- Monthly Heatmap (Month × Year) ---
    MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    heat_data = filtered.groupby(['Year', 'Month'])['Revenue'].sum().reset_index()
    heat_pivot = heat_data.pivot(index='Month', columns='Year', values='Revenue')
    heat_pivot = heat_pivot.reindex(MONTH_ORDER)

    heatmap = go.Figure(data=go.Heatmap(
        z=heat_pivot.values,
        x=[str(y) for y in heat_pivot.columns],
        y=heat_pivot.index,
        colorscale='YlOrRd',
        colorbar=dict(title='Revenue'),
    ))
    heatmap.update_layout(title='Revenue Heatmap (Month x Year)',
                          margin=dict(t=40, b=20))

    return kpis, trend, bar, pie, heatmap


def _kpi(title, value):
    return html.Div([
        html.Span(title, className='kpi-title'),
        html.Span(value, className='kpi-value'),
    ], className='kpi-card')


if __name__ == '__main__':
    app.run(debug=True)
