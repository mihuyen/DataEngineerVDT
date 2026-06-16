select *
from {{ ref('fact_daily_price_indicators') }}
where abs(market_cap - (close * shares_outstanding)) > 0.0001
