select *
from {{ ref('fact_daily_price_indicators') }}
where rsi_14 is not null and (rsi_14 < 0 or rsi_14 > 100)
