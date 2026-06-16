select *
from {{ ref('fact_daily_price_indicators') }}
where abs(macd - (ema_12 - ema_26)) > 0.0001
