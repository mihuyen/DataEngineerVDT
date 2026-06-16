select
    ticker,
    trading_date,
    count(*) as row_count
from {{ ref('fact_daily_price_indicators') }}
group by ticker, trading_date
having row_count > 1
