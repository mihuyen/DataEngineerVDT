IX. Thiết kế Dashboard cho hệ thống
Dashboard của hệ thống được thiết kế nhằm giúp người dùng theo dõi thị trường chứng khoán từ mức tổng quan đến chi tiết từng mã cổ phiếu. Các trang dashboard được chia theo từng nhóm nhu cầu chính: tổng quan thị trường, phân tích mã cổ phiếu, quét tín hiệu kỹ thuật, giám sát chất lượng dữ liệu, theo dõi realtime VWAP, phân tích tin tức/sentiment và lịch sử cảnh báo.
Hệ thống sử dụng Apache Superset cho các dashboard phân tích phục vụ nhà đầu tư, sử dụng Grafana để giám sát realtime metrics và trạng thái service, đồng thời sử dụng Airflow UI để theo dõi trạng thái DAG và task trong pipeline batch.

1. Trang Market Overview — Tổng quan thị trường
Mục đích
Trang Market Overview cung cấp cái nhìn nhanh về trạng thái chung của thị trường trong ngày. Người dùng có thể biết thị trường đang tăng hay giảm, thanh khoản ra sao, chỉ số chính biến động thế nào và nhóm ngành nào đang dẫn dắt thị trường.
Nguồn dữ liệu chính
fact_market_index
fact_daily_price
dim_stock
dim_sector
dim_date
Bộ lọc chính
Bộ lọc
Mô tả
Ngày giao dịch
Mặc định hiển thị phiên giao dịch gần nhất
Sàn giao dịch
HOSE, HNX, UPCOM
Ngành
Lọc theo nhóm ngành
Chỉ số
VN-Index, HNX-Index, VN30

Thông tin hiển thị
Nhóm thông tin
Nội dung
Chỉ số thị trường
VN-Index, HNX-Index, VN30
Biến động thị trường
Điểm tăng/giảm, % thay đổi so với phiên trước
Thanh khoản
Tổng khối lượng giao dịch, tổng giá trị giao dịch
Độ rộng thị trường
Số mã tăng, số mã giảm, số mã đứng giá
Ngành dẫn dắt
Ngành tăng mạnh nhất, ngành giảm mạnh nhất
Top cổ phiếu
Top tăng giá, top giảm giá, top thanh khoản, top vốn hóa

Biểu đồ nên dùng
Biểu đồ
Mục đích
KPI Card
Hiển thị VN-Index, % thay đổi, tổng giá trị giao dịch
Line Chart
Diễn biến VN-Index/VN30 theo thời gian
Bar Chart
Top 10 mã tăng mạnh nhất và top 10 mã giảm mạnh nhất
Horizontal Bar Chart
Top 10 mã có khối lượng hoặc giá trị giao dịch cao nhất
Donut Chart
Tỷ lệ số mã tăng, giảm, đứng giá
Heatmap
Hiệu suất theo ngành

Liên kết drill-down
Người dùng có thể nhấn vào mã cổ phiếu trong bảng Top tăng giá, Top giảm giá, Top thanh khoản hoặc Top vốn hóa để chuyển sang trang Stock Detail với mã cổ phiếu đó được chọn tự động.
Ví dụ insight người dùng nhận được
VN-Index tăng nhưng số mã giảm nhiều hơn số mã tăng, cho thấy thị trường phân hóa.
Ngành Ngân hàng đang dẫn dắt thị trường.
Một số mã có thanh khoản tăng đột biến so với trung bình 20 ngày.
Top vốn hóa giúp người dùng nhận biết các cổ phiếu có ảnh hưởng lớn đến chỉ số chung.

2. Trang Stock Detail — Phân tích chi tiết mã cổ phiếu
Mục đích
Trang Stock Detail cho phép người dùng chọn một mã cổ phiếu cụ thể để xem lịch sử giá, thanh khoản, vốn hóa, chỉ báo kỹ thuật và tin tức liên quan. Đây là trang quan trọng nhất đối với người dùng muốn phân tích sâu một cổ phiếu.
Nguồn dữ liệu chính
fact_daily_price
dim_stock
dim_sector
fact_news_sentiment_daily
dim_date
Bộ lọc chính
Bộ lọc
Mô tả
Mã cổ phiếu
Người dùng chọn một ticker cụ thể, ví dụ: VCB, FPT, HPG
Khoảng thời gian
1 tháng, 3 tháng, 6 tháng, 1 năm hoặc tùy chọn
Mặc định
Hiển thị 3 tháng gần nhất
Chỉ báo kỹ thuật
Bật/tắt SMA, EMA, Bollinger Band, RSI, MACD

Việc đặt mặc định 3 tháng gần nhất giúp dashboard hiển thị đủ xu hướng ngắn và trung hạn mà không làm biểu đồ quá dài hoặc khó đọc.
Thông tin hiển thị
Nhóm thông tin
Nội dung
Thông tin mã
Ticker, tên công ty, sàn, ngành, trạng thái niêm yết
Giá giao dịch
Open, High, Low, Close, Volume, Value
Biến động giá
Price change, pct_change
Vốn hóa
Market cap theo ngày
Chỉ báo xu hướng
SMA20, EMA12, EMA26
Chỉ báo động lượng
RSI14, MACD, MACD Signal
Chỉ báo biến động
Bollinger Band
Tin tức
Số lượng tin, số nguồn tin, sentiment trung bình, headline nổi bật

Biểu đồ nên dùng
Biểu đồ
Mục đích
Candlestick Chart
Hiển thị biến động OHLC theo ngày
Line Chart
Hiển thị SMA20, EMA12, EMA26 trên giá đóng cửa
Bar Chart
Khối lượng giao dịch theo ngày
Line Chart
RSI14 theo thời gian, kèm ngưỡng 30 và 70
Line Chart
MACD và MACD Signal
Line/Band Chart
Bollinger Band và giá đóng cửa
KPI Card
Close price, pct_change, volume, market_cap
Table
Tin tức nổi bật và điểm sentiment

Liên kết drill-down
Từ các bảng tin tức, bảng tín hiệu kỹ thuật hoặc bảng xếp hạng cổ phiếu, người dùng có thể nhấn vào mã cổ phiếu để chuyển sang trang Stock Detail và xem chi tiết lịch sử giá, chỉ báo và tin tức liên quan.
Ví dụ insight người dùng nhận được
Cổ phiếu VCB có RSI = 72, có thể đang rơi vào vùng quá mua.
Giá đóng cửa vượt Bollinger Band trên, thể hiện biến động mạnh.
Khối lượng hôm nay cao hơn trung bình 20 ngày, cho thấy dòng tiền tăng.
Tin tức tích cực xuất hiện cùng giai đoạn giá tăng, giúp người dùng có thêm ngữ cảnh phân tích.

3. Trang Technical Signal Scanner — Bộ lọc tín hiệu kỹ thuật
Mục đích
Trang Technical Signal Scanner tự động quét toàn bộ thị trường để tìm các mã có tín hiệu kỹ thuật đáng chú ý. Trang này giúp người dùng không cần tự tính từng chỉ báo mà vẫn có thể nhanh chóng phát hiện các mã có dấu hiệu quá mua, quá bán, breakout, breakdown hoặc thanh khoản đột biến.
Nguồn dữ liệu chính
fact_daily_price
dim_stock
dim_sector
dim_date
Bộ lọc chính
Bộ lọc
Mô tả
Ngày giao dịch
Mặc định là phiên giao dịch gần nhất
Sàn giao dịch
HOSE, HNX, UPCOM
Ngành
Lọc theo nhóm ngành
Loại tín hiệu
RSI, MACD, Bollinger Band, Volume breakout
Khoảng giá trị RSI
Cho phép lọc RSI theo khoảng tùy chọn
Khoảng thanh khoản
Lọc theo volume hoặc value

Thông tin hiển thị
Nhóm tín hiệu
Điều kiện gợi ý
Quá mua
rsi_14 > 70
Quá bán
rsi_14 < 30
Breakout
close > bb_upper
Breakdown
close < bb_lower
MACD tích cực
macd > macd_signal
Thanh khoản đột biến
volume > volume_sma_20 * 1.5
Tăng giá mạnh
pct_change thuộc top cao nhất
Giảm giá mạnh
pct_change thuộc top thấp nhất

Ngưỡng thanh khoản đột biến được đặt là volume > volume_sma_20 * 1.5. Ngưỡng 1.5 lần trung bình 20 ngày được chọn vì đủ để lọc ra các mã có thanh khoản tăng đáng kể, nhưng không quá khắt khe như ngưỡng 2 lần khiến số lượng mã phát hiện được quá ít. Trong phạm vi demo, ngưỡng này có thể cấu hình lại tùy theo nhu cầu phân tích.
Biểu đồ nên dùng
Biểu đồ
Mục đích
KPI Card
Số mã quá mua, quá bán, breakout, breakdown
Filter Table
Danh sách mã thỏa mãn từng tín hiệu
Bar Chart
Top mã có RSI cao nhất
Bar Chart
Top mã có RSI thấp nhất
Bar Chart
Top mã có volume tăng đột biến
Table
Danh sách mã có MACD tích cực hoặc giá vượt Bollinger Band

Không sử dụng Scatter Plot cho toàn bộ thị trường vì số lượng mã lớn có thể khiến biểu đồ khó đọc và khó demo. Thay vào đó, hệ thống ưu tiên bảng lọc và biểu đồ xếp hạng để người dùng dễ xác định mã cần quan tâm.
Liên kết drill-down
Người dùng có thể nhấn vào mã cổ phiếu trong bảng tín hiệu để chuyển sang trang Stock Detail và xem diễn biến giá, RSI, MACD, Bollinger Band của mã đó trong khoảng thời gian gần nhất.
Ví dụ insight người dùng nhận được
Có nhiều mã đang ở vùng quá mua, cho thấy thị trường có thể đang nóng.
Một số mã vượt Bollinger Band trên kèm thanh khoản cao, có thể đang có dòng tiền mạnh.
Các mã RSI thấp có thể được đưa vào danh sách theo dõi để tìm cơ hội hồi phục.

4. Trang Data Pipeline Monitor — Giám sát pipeline và chất lượng dữ liệu
Mục đích
Trang Data Pipeline Monitor dành cho admin, developer hoặc analyst nội bộ để theo dõi trạng thái pipeline thu thập, xử lý và kiểm soát chất lượng dữ liệu. Đây là điểm khác biệt quan trọng so với các ứng dụng chứng khoán thông thường, vì hệ thống không chỉ hiển thị dữ liệu mà còn giám sát độ tin cậy của dữ liệu.
Ghi chú về công cụ hiển thị
Trang Data Pipeline Monitor là trang tổng hợp các KPI và đường dẫn giám sát từ nhiều công cụ khác nhau.
Phần trạng thái DAG, lịch chạy và task lỗi được hiển thị qua Airflow UI.
Phần streaming health, Kafka consumer lag, trạng thái service và các chỉ số vận hành realtime được hiển thị qua Grafana.
Phần data quality có thể lấy từ Great Expectations validation results, dbt test results và hiển thị lại trên Superset hoặc trang giám sát nội bộ.
Trang này đóng vai trò như một trang tổng hợp, giúp người vận hành truy cập nhanh các thông tin quan trọng thay vì phải mở từng công cụ riêng lẻ.
Nguồn dữ liệu chính
Airflow task logs
Great Expectations validation results
dbt test results
Kafka consumer lag
ClickHouse system tables
MinIO object metadata
Grafana metrics
Thông tin hiển thị
Nhóm thông tin
Công cụ hiển thị chính
Nội dung
Trạng thái pipeline batch
Airflow UI
DAG success/fail, thời gian chạy gần nhất, task bị lỗi
Ingestion volume
Airflow UI / Superset
Số bản ghi ingest theo ngày, số file ghi vào Bronze/Silver
Data quality
Great Expectations / dbt / Superset
Số lỗi GX validation, số test dbt pass/fail
Streaming health
Grafana
Kafka consumer lag, số message xử lý mỗi phút
Storage health
Grafana / MinIO Console
Dung lượng MinIO, số object theo từng layer Bronze/Silver
Serving health
Grafana / ClickHouse system tables
Trạng thái ClickHouse, thời gian query trung bình

Biểu đồ nên dùng
Biểu đồ
Mục đích
KPI Card
Số DAG thành công/thất bại, số lỗi validation
Line Chart
Số bản ghi ingest theo ngày
Bar Chart
Số lỗi data quality theo loại lỗi
Table
Danh sách task Airflow thất bại gần nhất
Line Chart
Kafka consumer lag theo thời gian
Gauge/Stat Panel
Trạng thái service: Kafka, ClickHouse, MinIO, Airflow

Ví dụ insight admin nhận được
Pipeline OHLCV hôm nay chạy thành công nhưng có một số mã bị thiếu dữ liệu.
Great Expectations phát hiện lỗi high < low ở một số bản ghi.
dbt test fail do có bản ghi trùng khóa (ticker, date_id).
Kafka consumer lag tăng bất thường, cần kiểm tra streaming consumer.
ClickHouse query dashboard vẫn nằm trong ngưỡng chấp nhận được.

5. Trang Realtime VWAP Monitoring — Theo dõi realtime trong phiên
Mục đích
Trang Realtime VWAP Monitoring theo dõi biến động intraday của cổ phiếu theo từng phút, đặc biệt là so sánh giá hiện tại với VWAP theo phút và VWAP lũy kế từ đầu phiên. Trang này phục vụ nhu cầu giám sát thị trường trong phiên và hỗ trợ Alert Engine phát hiện các biến động bất thường.
Nguồn dữ liệu chính
fact_realtime_vwap
dim_stock
fact_alert_event
Thời gian hoạt động
Dashboard này hiển thị dữ liệu realtime trong giờ giao dịch, từ khoảng 9:00 đến 14:45. Ngoài giờ giao dịch, dashboard hiển thị dữ liệu của phiên giao dịch gần nhất thay vì dữ liệu live.
Trong trường hợp nguồn dữ liệu realtime bị giới hạn hoặc API không ổn định, hệ thống có thể demo bằng dữ liệu giả lập từ lịch sử để chứng minh luồng Kafka → ClickHouse → Dashboard vẫn hoạt động đúng.
Bộ lọc chính
Bộ lọc
Mô tả
Mã cổ phiếu
Chọn ticker cần theo dõi
Ngày giao dịch
Mặc định là phiên hiện tại hoặc phiên gần nhất
Khoảng thời gian trong phiên
Sáng, chiều hoặc tùy chọn theo phút
Ngưỡng lệch VWAP
Ví dụ: 1%, 2%, 3%

Thông tin hiển thị
Nhóm thông tin
Nội dung
Giá realtime
Open, High, Low, Close theo từng phút
VWAP
VWAP 1 phút và session VWAP
Thanh khoản intraday
Volume từng phút, session volume
Độ lệch VWAP
price_vs_vwap_pct, price_vs_session_vwap_pct
Cảnh báo realtime
Số cảnh báo đã kích hoạt trong phiên

Biểu đồ nên dùng
Biểu đồ
Mục đích
Line Chart
Giá theo phút và session VWAP
Bar Chart
Khối lượng giao dịch từng phút
Line Chart
price_vs_session_vwap_pct theo thời gian
Table
Danh sách mã lệch VWAP mạnh nhất
KPI Card
Session volume, session VWAP, số alert trong phiên

Liên kết drill-down
Người dùng có thể nhấn vào mã cổ phiếu trong bảng lệch VWAP để chuyển sang trang Stock Detail hoặc xem lịch sử cảnh báo liên quan tại trang Alert History.
Ví dụ insight người dùng nhận được
Giá hiện tại của VCB đang cao hơn session VWAP 1.8%.
Thanh khoản tăng mạnh trong 10 phút gần nhất.
Một số mã đang lệch khỏi VWAP quá ngưỡng và đã kích hoạt cảnh báo.

6. Trang News & Sentiment — Tin tức và cảm xúc thị trường
Mục đích
Trang News & Sentiment giúp người dùng theo dõi mức độ xuất hiện trên truyền thông và cảm xúc tin tức liên quan đến từng mã cổ phiếu. Trang này bổ sung góc nhìn dữ liệu phi cấu trúc vào hệ thống phân tích thị trường.
Nguồn dữ liệu chính
fact_news_sentiment_daily
dim_stock
dim_sector
dim_date
Bộ lọc chính
Bộ lọc
Mô tả
Ngày hoặc khoảng ngày
Chọn ngày cụ thể hoặc khoảng thời gian
Mã cổ phiếu
Lọc theo ticker
Ngành
Lọc theo nhóm ngành
Sentiment
Positive, Negative, Neutral
Số nguồn tin tối thiểu
Lọc các mã được nhiều nguồn đề cập

Thông tin hiển thị
Nhóm thông tin
Nội dung
Số lượng tin
news_count theo mã và theo ngày
Số nguồn tin
source_count
Sentiment
positive_count, negative_count, neutral_count
Điểm cảm xúc
avg_sentiment_score
Tin nổi bật
top_headline
So sánh theo ngành
Ngành có sentiment tích cực/tiêu cực nhất

Biểu đồ nên dùng
Biểu đồ
Mục đích
Bar Chart
Top mã có nhiều tin nhất
Stacked Bar Chart
Số tin tích cực, tiêu cực, trung lập
Line Chart
Sentiment score theo thời gian
Heatmap
Sentiment trung bình theo ngành
Table
Headline nổi bật theo từng mã

Liên kết drill-down
Người dùng có thể nhấn vào mã cổ phiếu trong bảng tin tức để chuyển sang trang Stock Detail và xem liệu biến động giá có cùng chiều với sentiment hay không.
Ví dụ insight người dùng nhận được
Một mã có 10 tin trong ngày nhưng chỉ đến từ 2 nguồn, mức độ lan tỏa chưa cao.
Một ngành có sentiment tiêu cực tăng mạnh trong vài ngày gần đây.
Tin tức tích cực xuất hiện cùng thời điểm giá và thanh khoản tăng.

7. Trang Alert History — Lịch sử cảnh báo người dùng
Mục đích
Trang Alert History cho phép người dùng xem lại các cảnh báo đã được kích hoạt, điều kiện kích hoạt, giá trị thực tế và trạng thái gửi cảnh báo. Trang này cũng giúp admin kiểm tra hệ thống có từng gửi cảnh báo lặp hoặc spam hay không.
Cần phân biệt rõ: bộ lọc trên dashboard chỉ dùng để xem lại lịch sử cảnh báo, còn logic chống spam được thực thi trong Alert Checker trước khi cảnh báo được gửi đi.
Nguồn dữ liệu chính
fact_alert_event
dim_stock
dim_date
Bộ lọc chính
Bộ lọc
Mô tả
Người dùng
Lọc theo user_id
Mã cổ phiếu
Lọc theo ticker
Loại cảnh báo
RSI_ABOVE, RSI_BELOW, BB_BREAK, PRICE_BELOW, PRICE_ABOVE, VWAP_DEVIATION
Kênh gửi
TELEGRAM, EMAIL
Trạng thái gửi
Đã gửi, chưa gửi, lỗi gửi
Khoảng thời gian
Hôm nay, 7 ngày gần nhất, 30 ngày gần nhất hoặc tùy chọn
Khoảng cách tối thiểu giữa các alert
Lọc các cảnh báo trùng điều kiện trong vòng 30/60 phút để kiểm tra lịch sử có xuất hiện cảnh báo lặp hay không

Bộ lọc chống spam trên dashboard giúp người dùng và admin xem lại lịch sử để phát hiện các cảnh báo bị kích hoạt quá sát nhau. Tuy nhiên, bộ lọc này không phải là nơi ngăn gửi cảnh báo. Việc ngăn gửi cảnh báo trùng lặp được thực hiện ở tầng xử lý Alert Engine.
Cơ chế chống spam trong Alert Engine
Cơ chế chống spam được thực thi tại Alert Checker trước khi hệ thống gửi cảnh báo qua Telegram hoặc Email.
Quy trình xử lý như sau:
Alert Checker đọc cấu hình cảnh báo đang bật từ bảng user_alerts trong PostgreSQL.
Alert Checker truy vấn dữ liệu mới nhất từ ClickHouse, ví dụ RSI, Bollinger Band, giá hiện tại hoặc độ lệch so với session VWAP.
Khi điều kiện cảnh báo được kích hoạt, hệ thống chưa gửi ngay mà kiểm tra bảng fact_alert_event trong ClickHouse.
Hệ thống kiểm tra xem cùng một tổ hợp user_id + ticker + condition_type đã được gửi trong vòng N phút gần nhất hay chưa.
Nếu đã có cảnh báo tương tự trong khoảng thời gian N phút, hệ thống bỏ qua lần kích hoạt hiện tại để tránh spam.
Nếu chưa có cảnh báo tương tự, hệ thống gửi thông báo qua Telegram hoặc Email, sau đó ghi một bản ghi mới vào fact_alert_event.
Giá trị N mặc định là 30 phút và có thể cấu hình trong bảng user_alerts. Ví dụ, người dùng có thể đặt cooldown 30 phút hoặc 60 phút tùy mức độ nhạy cảm của cảnh báo.
Ví dụ logic kiểm tra chống spam:
Kiểm tra trước khi gửi alert:

user_id = user_001
ticker = VCB
condition_type = RSI_ABOVE
cooldown_minutes = 30

Nếu đã tồn tại bản ghi trong fact_alert_event
với cùng user_id, ticker, condition_type
và triggered_at >= now() - 30 phút
thì không gửi lại cảnh báo.

Ngược lại, gửi cảnh báo và ghi log vào fact_alert_event.

Về mặt kỹ thuật, cơ chế này giúp tách biệt rõ hai phần:
Thành phần
Vai trò
user_alerts trong PostgreSQL
Lưu cấu hình cảnh báo của người dùng: mã cổ phiếu, điều kiện, ngưỡng, kênh gửi, cooldown
fact_alert_event trong ClickHouse
Lưu lịch sử các cảnh báo đã kích hoạt và đã gửi
Alert Checker
Thực thi logic kiểm tra điều kiện và chống spam trước khi gửi cảnh báo
Alert History Dashboard
Hiển thị lại lịch sử cảnh báo và hỗ trợ kiểm tra cảnh báo trùng lặp

Cách thiết kế này giúp hệ thống vừa tránh làm phiền người dùng bởi các cảnh báo lặp lại, vừa vẫn giữ đầy đủ lịch sử cảnh báo để phục vụ kiểm tra và phân tích sau này.
Thông tin hiển thị
Nhóm thông tin
Nội dung
Lịch sử cảnh báo
Thời điểm kích hoạt, mã cổ phiếu, loại điều kiện
Ngưỡng cảnh báo
threshold_value
Giá trị thực tế
actual_value
Kênh gửi
TELEGRAM hoặc EMAIL
Trạng thái gửi
is_sent, sent_at
Cooldown
Thời gian tối thiểu trước khi gửi lại cảnh báo cùng loại
Thống kê alert
Số alert theo ngày, theo mã, theo loại điều kiện

Biểu đồ nên dùng
Biểu đồ
Mục đích
Table
Lịch sử cảnh báo chi tiết
Bar Chart
Số cảnh báo theo ngày
Donut Chart
Tỷ lệ cảnh báo theo condition_type
Bar Chart
Top mã kích hoạt nhiều cảnh báo nhất
KPI Card
Tổng số alert, số alert đã gửi, số alert lỗi
Table
Danh sách cảnh báo có dấu hiệu bị kích hoạt lặp trong thời gian ngắn

Liên kết drill-down
Người dùng có thể nhấn vào mã cổ phiếu trong bảng lịch sử cảnh báo để chuyển sang trang Stock Detail hoặc trang Realtime VWAP Monitoring nếu cảnh báo liên quan đến VWAP.
Ví dụ insight người dùng nhận được
Người dùng nhận nhiều cảnh báo nhất ở nhóm RSI_ABOVE.
Một mã cổ phiếu liên tục kích hoạt cảnh báo VWAP_DEVIATION trong phiên.
Có thể kiểm tra cảnh báo đã gửi thành công qua Telegram hoặc Email chưa.
Có thể phát hiện hệ thống từng kích hoạt nhiều cảnh báo giống nhau trong khoảng thời gian ngắn.

Cơ chế điều hướng giữa các trang
Dashboard được thiết kế theo hướng drill-down, giúp người dùng đi từ bức tranh tổng quan đến phân tích chi tiết.
Từ trang
Hành động
Chuyển đến
Market Overview
Nhấn vào mã trong Top tăng/giảm/thanh khoản/vốn hóa
Stock Detail
Technical Signal Scanner
Nhấn vào mã có tín hiệu kỹ thuật
Stock Detail
Realtime VWAP Monitoring
Nhấn vào mã lệch VWAP mạnh
Stock Detail hoặc Alert History
News & Sentiment
Nhấn vào mã có tin nổi bật
Stock Detail
Alert History
Nhấn vào mã trong lịch sử cảnh báo
Stock Detail
Data Pipeline Monitor
Nhấn vào pipeline lỗi
Airflow UI hoặc Grafana chi tiết

Cơ chế drill-down giúp người dùng không chỉ xem dữ liệu tổng quan mà còn nhanh chóng truy vết đến nguyên nhân hoặc chi tiết của từng mã cổ phiếu.

Thứ tự ưu tiên triển khai Dashboard
Nếu thời gian triển khai có hạn, nên ưu tiên theo thứ tự sau:
Mức độ ưu tiên
Trang dashboard
Lý do
Bắt buộc
Market Overview
Cho thấy toàn cảnh thị trường và giá trị tổng quan của hệ thống
Bắt buộc
Stock Detail
Thể hiện rõ năng lực phân tích kỹ thuật của hệ thống
Bắt buộc
Technical Signal Scanner
Chứng minh hệ thống không chỉ lưu dữ liệu mà còn tạo insight
Bắt buộc
Data Pipeline Monitor
Thể hiện điểm khác biệt của kiến trúc Data Lakehouse: dữ liệu có kiểm soát chất lượng, có giám sát pipeline và có khả năng phát hiện lỗi
Nên có
Realtime VWAP Monitoring
Thể hiện năng lực streaming và realtime analytics, nhưng phụ thuộc vào độ ổn định của nguồn dữ liệu realtime
Nâng cao
News & Sentiment
Bổ sung dữ liệu phi cấu trúc và yếu tố truyền thông
Nâng cao
Alert History
Hoàn thiện use case cảnh báo cá nhân hóa

Trong phạm vi đồ án, bốn trang quan trọng nhất cần hoàn thiện là Market Overview, Stock Detail, Technical Signal Scanner và Data Pipeline Monitor. Đây là nhóm dashboard thể hiện rõ nhất giá trị cốt lõi của hệ thống: thu thập dữ liệu, chuẩn hóa dữ liệu, phân tích kỹ thuật và kiểm soát chất lượng dữ liệu.
Trang Realtime VWAP Monitoring nên được triển khai nếu pipeline streaming hoạt động ổn định. Trong trường hợp API realtime bị giới hạn hoặc không ổn định, hệ thống có thể demo bằng dữ liệu giả lập từ lịch sử để chứng minh luồng Kafka → ClickHouse → Dashboard vẫn hoạt động đúng.


