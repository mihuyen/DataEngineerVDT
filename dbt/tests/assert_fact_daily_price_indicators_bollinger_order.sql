select *
from {{ ref('fact_daily_price_indicators') }}
where bb_upper is not null
  and (bb_upper < bb_middle or bb_middle < bb_lower)
