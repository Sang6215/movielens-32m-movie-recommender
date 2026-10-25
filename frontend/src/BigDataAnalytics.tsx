import { useEffect, useId, useState, type ReactNode } from "react";
import { getAnalytics } from "./api";
import type { AnalyticsResponse, ChartPoint } from "./types";
import "./analytics.css";

const number = new Intl.NumberFormat("vi-VN");
const decimal = (value: number, digits = 3) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: digits }).format(value);
const compact = (value: number) => new Intl.NumberFormat("vi-VN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
const percent = (value: number) => `${decimal(value * 100, 4)}%`;
const date = (value: string) => value.split("-").reverse().join("/");
const genreNames: Record<string, string> = {
  Drama: "Chính kịch", Comedy: "Hài", Thriller: "Giật gân", Romance: "Lãng mạn", Action: "Hành động",
  Documentary: "Tài liệu", Horror: "Kinh dị", "(no genres listed)": "Chưa phân loại", Crime: "Tội phạm",
  Adventure: "Phiêu lưu", "Sci-Fi": "Khoa học viễn tưởng", Animation: "Hoạt hình", Children: "Thiếu nhi",
  Mystery: "Bí ẩn", Fantasy: "Giả tưởng", War: "Chiến tranh", Western: "Cao bồi", Musical: "Nhạc kịch", "Film-Noir": "Film Noir", IMAX: "IMAX",
};
const tabs = [{ id: "data", label: "Dữ liệu MovieLens" }, { id: "performance", label: "Hiệu năng Spark" }, { id: "model", label: "Kết quả ALS" }, { id: "pipeline", label: "Quy trình Big Data" }] as const;
type Tab = typeof tabs[number]["id"];

function Panel({ title, subtitle, children, wide = false }: { title: string; subtitle: string; children: ReactNode; wide?: boolean }) {
  return <article className={`analytics-panel${wide ? " analytics-wide" : ""}`}><div className="analytics-panel-heading"><h3>{title}</h3><p>{subtitle}</p></div>{children}</article>;
}

function DataTable({ points, unit, format }: { points: ChartPoint[]; unit: string; format: (value: number) => string }) {
  return <details className="analytics-data-table"><summary>Xem bảng số liệu</summary><table><thead><tr><th scope="col">Nhóm</th><th scope="col">{unit}</th></tr></thead><tbody>{points.map(point => <tr key={point.label}><th scope="row">{point.label}</th><td>{format(point.value)}</td></tr>)}</tbody></table></details>;
}

function Bars({ points, unit, format = value => number.format(value), color = "gold" }: { points: ChartPoint[]; unit: string; format?: (value: number) => string; color?: "gold" | "teal" }) {
  const [selected, setSelected] = useState(0);
  const maximum = Math.max(...points.map(point => point.value), 1e-10);
  const current = points[Math.min(selected, points.length - 1)];
  return <div className={`analytics-bars analytics-${color}`}>
    <div className="analytics-chart-readout" aria-live="polite"><span>{current?.label}</span><strong>{current ? format(current.value) : "—"} <small>{unit}</small></strong></div>
    <div className="analytics-bar-rows">{points.map((point, index) => <button type="button" key={point.label} className={`analytics-bar-row${selected === index ? " selected" : ""}`} aria-pressed={selected === index} onMouseEnter={() => setSelected(index)} onFocus={() => setSelected(index)} onClick={() => setSelected(index)}>
      <span className="analytics-bar-label">{point.label}</span><span className="analytics-bar-track"><span style={{ width: `${point.value / maximum * 100}%` }} /></span><strong>{format(point.value)}</strong>
    </button>)}</div><DataTable points={points} unit={unit} format={format} />
  </div>;
}

function LineChart({ points, unit, zero = true, format = value => number.format(value) }: { points: ChartPoint[]; unit: string; zero?: boolean; format?: (value: number) => string }) {
  const [selected, setSelected] = useState(points.length - 1);
  const chartId = useId();
  const minValue = Math.min(...points.map(point => point.value));
  const maxValue = Math.max(...points.map(point => point.value));
  const minimum = zero ? 0 : Math.floor(minValue * 100) / 100;
  const maximum = zero ? maxValue * 1.12 : Math.ceil(maxValue * 100) / 100;
  const span = maximum - minimum || 1;
  const x = (index: number) => 66 + index * 660 / Math.max(points.length - 1, 1);
  const y = (value: number) => 220 - (value - minimum) / span * 175;
  const polyline = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");
  const current = points[selected] ?? points[0];
  return <div className="analytics-line-chart">
    <div className="analytics-chart-readout" aria-live="polite"><span>{current.label}</span><strong>{format(current.value)} <small>{unit}</small></strong></div>
    <svg viewBox="0 0 760 266" role="group" aria-label={`Biểu đồ ${unit}; chọn một điểm để xem số liệu`}>
      <defs><linearGradient id={chartId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f5c518" stopOpacity=".22" /><stop offset="100%" stopColor="#f5c518" stopOpacity="0" /></linearGradient></defs>
      {[0, 1, 2, 3, 4].map(tick => { const value = minimum + span * tick / 4; return <g key={tick}><line x1="66" x2="726" y1={y(value)} y2={y(value)} className="analytics-grid-line" /><text x="56" y={y(value) + 4} textAnchor="end">{zero ? compact(value) : decimal(value, 3)}</text></g>; })}
      <polygon points={`66,220 ${polyline} 726,220`} fill={`url(#${chartId})`} />
      <polyline points={polyline} fill="none" stroke="#f5c518" strokeWidth="2.7" />
      {points.map((point, index) => <g key={point.label}>
        <circle cx={x(index)} cy={y(point.value)} r={selected === index ? 6 : 4} fill={selected === index ? "#f5c518" : "#171a20"} stroke="#f5c518" strokeWidth="2" tabIndex={0} role="button" aria-label={`${point.label}: ${format(point.value)} ${unit}`} aria-pressed={selected === index} onMouseEnter={() => setSelected(index)} onFocus={() => setSelected(index)} onClick={() => setSelected(index)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(index); } }}><title>{point.label}: {format(point.value)}</title></circle>
        {(points.length <= 6 || index % 4 === 0 || index === points.length - 1) && <text x={x(index)} y="248" textAnchor="middle">{point.label}</text>}
      </g>)}
    </svg>
    {!zero && <p className="analytics-caption">Trục tung thu gọn từ {decimal(minimum)} đến {decimal(maximum)} để thể hiện mức thay đổi.</p>}
    <DataTable points={points} unit={unit} format={format} />
  </div>;
}

function DatasetView({ data }: { data: AnalyticsResponse }) {
  const [allGenres, setAllGenres] = useState(false);
  const dataset = data.dataset;
  const genres = dataset.genres.slice(0, allGenres ? undefined : 10).map(point => ({ ...point, label: genreNames[point.label] ?? point.label }));
  const highRatings = dataset.ratingsDistribution.filter(point => Number(point.label) >= 4).reduce((sum, point) => sum + point.value, 0);
  return <div className="analytics-grid">
    <Panel title="Người xem chấm phim bao nhiêu sao?" subtitle="Phân bố 32 triệu lượt đánh giá · thang 0,5–5 sao">
      <Bars points={dataset.ratingsDistribution.map(point => ({ ...point, label: `${point.label.replace(".", ",")} ★` }))} unit="lượt chấm" />
      <p className="analytics-insight"><strong>{percent(highRatings / dataset.ratings)}</strong> lượt chấm từ 4 sao trở lên. Đây là đánh giá được ghi nhận, không phải tỷ lệ khách hiện tại thích phim.</p>
    </Panel>
    <Panel title="Thể loại nào có nhiều phim?" subtitle="Số đầu phim trong toàn bộ danh mục MovieLens">
      <div className="analytics-inline-controls"><button type="button" aria-pressed={allGenres} onClick={() => setAllGenres(!allGenres)}>{allGenres ? "Rút gọn Top 10" : "Xem đủ 20 nhóm"}</button></div>
      <Bars points={genres} unit="phim" color="teal" />
      <p className="analytics-caption">Một phim có thể thuộc nhiều thể loại. Tổng số đếm thể loại có thể lớn hơn {number.format(dataset.movies)} phim; nhóm chưa phân loại vẫn được giữ.</p>
    </Panel>
    <Panel title="Lịch sử đánh giá qua các năm" subtitle="Năm người dùng chấm điểm, không phải năm phát hành phim" wide>
      <LineChart points={dataset.ratingsByYear} unit="lượt chấm" />
      <p className="analytics-caption">Dữ liệu từ {dataset.firstRating.slice(0, 10)} đến {dataset.lastRating.slice(0, 10)}. Năm 2023 chỉ ghi nhận đến ngày 13/10, nên không phải một năm đầy đủ.</p>
    </Panel>
    <div className="analytics-context analytics-wide"><div><strong>{percent(dataset.sparsity)}</strong><span>độ thưa ma trận user–phim</span></div><p>{number.format(dataset.ratedMovies)} phim có ít nhất một rating trong dữ liệu nguồn. ALS xử lý các tương tác đã quan sát thay vì dựng ma trận đặc gồm mọi cặp user và phim.</p></div>
  </div>;
}

function PerformanceView({ data }: { data: AnalyticsResponse }) {
  const [dataset, setDataset] = useState("ratings");
  const performance = data.performance;
  const storage = performance.storage.find(row => row.dataset === dataset)!;
  return <div className="analytics-grid">
    <Panel title="CSV và Parquet khác nhau về dung lượng" subtitle="Dung lượng tệp sau chuyển đổi trên filesystem local">
      <label className="analytics-select">Bảng dữ liệu<select value={dataset} onChange={event => setDataset(event.target.value)}>{performance.storage.map(row => <option key={row.dataset} value={row.dataset}>{row.dataset}</option>)}</select></label>
      <Bars key={dataset} points={[{ label: "CSV", value: storage.csv_size_mb }, { label: "Parquet", value: storage.parquet_size_mb }]} unit="MB" format={value => decimal(value, 2)} />
      <p className="analytics-insight">{storage.space_saving_pct >= 0 ? <>Giảm <strong>{decimal(storage.space_saving_pct, 2)}%</strong> dung lượng.</> : <>Parquet lớn hơn <strong>{decimal(-storage.space_saving_pct, 2)}%</strong> do overhead ở bảng nhỏ.</>}</p>
    </Panel>
    <Panel title="Đọc và tổng hợp toàn bộ 32M rating" subtitle={`Trung vị ${performance.query.runs} lần đo · Spark ${performance.query.master} · thời gian thấp hơn tốt hơn`}>
      <Bars points={[{ label: "CSV", value: performance.query.csv_median_sec }, { label: "Parquet", value: performance.query.parquet_median_sec }]} unit="giây" format={value => decimal(value)} color="teal" />
      <p className="analytics-insight">Parquet nhanh hơn <strong>{decimal(performance.query.parquet_speedup_x, 2)} lần</strong> trong truy vấn đọc ratings và groupBy movieId đã đo.</p>
      <p className="analytics-caption">CSV: {performance.query.csv_times_sec.map(value => decimal(value)).join(" / ")} giây. Parquet: {performance.query.parquet_times_sec.map(value => decimal(value)).join(" / ")} giây. Kết quả phụ thuộc truy vấn, máy và cache.</p>
    </Panel>
    <Panel title="Tăng số luồng Spark trên cùng một máy" subtitle="Nạp và cache dữ liệu, fit ALS 5 vòng và đánh giá trên sample" wide>
      <Bars points={performance.threads.map(row => ({ label: row.master, value: row.total_sec }))} unit="giây" format={value => decimal(value)} />
      <p className="analytics-insight">4 luồng nhanh hơn <strong>{decimal(performance.threads[2].speedup_vs_1_thread, 2)} lần</strong> so với 1 luồng trên sample {number.format(performance.threads[0].train_rows)} dòng train.</p>
      <p className="analytics-caption">Đây là so sánh local[1/2/4], chưa phải benchmark cụm nhiều máy hoặc hiệu năng HDFS.</p>
    </Panel>
  </div>;
}

function ModelView({ data }: { data: AnalyticsResponse }) {
  const [metric, setMetric] = useState<"precision" | "recall" | "ndcg">("precision");
  const model = data.model;
  const splits = [{ label: "Train", value: model.trainRows }, { label: "Validation", value: model.validationRows }, { label: "Test", value: model.testRows }];
  const metricNames = { precision: "Precision@10", recall: "Recall@10", ndcg: "NDCG@10" };
  return <div className="analytics-grid">
    <Panel title="Tăng vòng lặp có giúp model tốt hơn?" subtitle={`RMSE validation · rank ${model.params.rank} · regParam ${decimal(model.params.regParam, 2)} · thấp hơn tốt hơn`}>
      <LineChart points={model.tuning.map(row => ({ label: `${row.iterations} vòng`, value: row.rmse }))} unit="RMSE" zero={false} format={value => decimal(value, 6)} />
      <p className="analytics-caption">Chọn {model.params.maxIter} vòng vì tốt nhất trong 4 cấu hình đã thử. Chưa kết luận tăng vòng tiếp sẽ luôn tốt hơn.</p>
    </Panel>
    <Panel title="Kết quả trên tập test được giữ riêng" subtitle="Model cuối fit lại trên train cộng validation">
      <div className="analytics-test-metrics"><div><span>RMSE</span><strong>{decimal(model.test.rmse, 6)}</strong></div><div><span>MAE</span><strong>{decimal(model.test.mae, 6)}</strong></div><div><span>Coverage</span><strong>{percent(model.test.coverage)}</strong></div></div>
      <p className="analytics-caption">Có dự đoán cho {number.format(model.test.rows)} / {number.format(model.testRows)} cặp rating test. {number.format(model.testRows - model.test.rows)} dòng thiếu vector không tham gia RMSE/MAE nhưng vẫn nằm trong mẫu số coverage.</p>
      <p className="analytics-insight">RMSE đo sai số theo đơn vị rating. <strong>Coverage không phải độ chính xác.</strong> Các chỉ số này thuộc ALS, chưa đánh giá chức năng hồ sơ “Đã xem”.</p>
    </Panel>
    <Panel title="Dữ liệu được chia để huấn luyện ra sao?" subtitle="Sắp theo thời gian trong từng user; test không tham gia fit" wide>
      <div className="analytics-split" aria-label="Tỷ lệ train validation và test">{splits.map((split, index) => <span key={split.label} className={`split-${index}`} style={{ flex: split.value }} title={`${split.label}: ${number.format(split.value)} dòng`} />)}</div>
      <div className="analytics-split-labels">{splits.map((split, index) => <div key={split.label}><span className={`split-dot split-${index}`} />{split.label}<strong>{number.format(split.value)}</strong><small>{percent(split.value / data.dataset.ratings)}</small></div>)}</div>
      <p className="analytics-caption">Fit cuối: {number.format(model.fitRows)} dòng train + validation. Chia thời gian theo user chưa tạo một mốc cắt thời gian toàn cục.</p>
    </Panel>
    <Panel title="Đo khả năng xếp hạng Top 10" subtitle={`${number.format(model.rankingUsers)} user · phim liên quan có rating ≥4 · cao hơn tốt hơn`} wide>
      <div className="analytics-inline-controls" aria-label="Chọn chỉ số xếp hạng">{(["precision", "recall", "ndcg"] as const).map(key => <button key={key} type="button" aria-pressed={metric === key} onClick={() => setMetric(key)}>{metricNames[key]}</button>)}</div>
      <Bars key={metric} points={model.ranking.map(row => ({ label: row.label, value: row[metric] }))} unit={metricNames[metric]} format={value => decimal(value, 6)} color="teal" />
      <p className="analytics-insight">Popularity đang đạt {metricNames[metric]} cao nhất trong phép đo này. <strong>Chưa chứng minh ALS tốt hơn popularity.</strong></p>
      <p className="analytics-caption">Tập ứng viên khác nhau: {model.ranking.map(row => `${row.label}: ${number.format(row.candidates)} phim`).join("; ")}. Bộ lọc được điều chỉnh sau chẩn đoán test; cần tập ứng viên chung và holdout mới để xác nhận. Phim chưa được user chấm không đồng nghĩa họ không thích.</p>
    </Panel>
  </div>;
}

function PipelineView({ data }: { data: AnalyticsResponse }) {
  const [stage, setStage] = useState(0);
  const stages = [
    { title: "Chuẩn bị dữ liệu", tag: "CSV → PARQUET", text: "Kiểm tra schema, ID, rating và timestamp; chuyển 4 bảng MovieLens sang Parquet và tổng hợp EDA. Dữ liệu lớn được xử lý offline.", files: "00_check_data → 01_convert_to_parquet → 02_eda_local" },
    { title: "Huấn luyện và đánh giá", tag: "SPARK ALS", text: "Chia thời gian theo user, chọn số vòng bằng validation, fit cuối trên train + validation và đánh giá test. Xuất catalog, vector và chỉ mục lịch sử.", files: "03_prepare_splits → 04_train_als → 05_tune_evaluate → 12_prepare_als_serving" },
    { title: "Phục vụ trên website", tag: "FASTAPI → REACT", text: "Backend đọc artifact đã đóng gói để tính gợi ý bằng NumPy. Hồ sơ mới dùng lịch sử thể loại riêng; TMDB bổ sung poster. Không khởi chạy Spark hoặc train trong mỗi request.", files: "Catalog + vector → FastAPI → React → người xem" },
  ];
  return <div className="analytics-grid">
    <Panel title="Từ 32 triệu tương tác đến một gợi ý phim" subtitle="Chọn từng bước để xem cách Big Data tham gia sản phẩm" wide>
      <div className="analytics-pipeline">{stages.map((item, index) => <button key={item.title} type="button" aria-pressed={stage === index} onClick={() => setStage(index)}><span className="analytics-stage-number">0{index + 1}</span><small>{item.tag}</small><strong>{item.title}</strong>{index < 2 && <span className="analytics-flow-arrow" aria-hidden="true">→</span>}</button>)}</div>
      <div className="analytics-stage-description" aria-live="polite"><h4>{stages[stage].title}</h4><p>{stages[stage].text}</p><span>{stages[stage].files}</span></div>
    </Panel>
    <Panel title="Nhánh kiểm chứng Spark và HDFS" subtitle={`Kết quả ghi nhận ngày ${date(data.hdfs.date)} · không phải trạng thái cụm đang chạy`} wide>
      <div className="analytics-hdfs-flow"><span>4 CSV trên HDFS</span><b aria-hidden="true">→</b><span>Spark kiểm tra và ghi Parquet</span><b aria-hidden="true">→</b><span>Đọc lại và đối soát</span><b aria-hidden="true">→</b><span>Suy luận từ vector đã có</span></div>
      <div className="analytics-hdfs-metrics"><div><strong>{number.format(data.hdfs.readbackRows)}</strong><span>rating đọc lại</span></div><div><strong>{data.hdfs.dataNodes}</strong><span>DataNode trên một máy</span></div><div><strong>{data.hdfs.invalidRows}</strong><span>dòng rating không hợp lệ</span></div><div><strong>{data.hdfs.duplicates}</strong><span>bản ghi trùng hoàn toàn</span></div></div>
      <p className="analytics-caption">Spark {data.hdfs.sparkVersion} · Hadoop {data.hdfs.hadoopVersion} · {data.hdfs.sparkMaster}. Lần kiểm chứng {data.hdfs.success ? "đạt" : "chưa đạt"}; model_retrained={String(data.hdfs.modelRetrained)}. Train và benchmark ban đầu chạy local; HDFS bổ sung kiểm chứng ETL và suy luận. Chưa có thử nghiệm chịu lỗi trên cụm nhiều máy.</p>
    </Panel>
    <Panel title="Dữ liệu MovieLens và hồ sơ demo được tách riêng" subtitle="Hai nguồn phản hồi phục vụ hai cách gợi ý" wide>
      <div className="analytics-two-paths"><div><span>MOVIELENS USER ID</span><h4>Vector ALS đã huấn luyện</h4><p>Rating lịch sử → vector user/phim → điểm ALS → Top 10 chưa chấm.</p></div><div><span>HỒ SƠ TRÌNH DUYỆT</span><h4>Thể loại từ phim Đã xem</h4><p>Đánh dấu phim → đếm thể loại → loại phim đã xem → tối đa 12 gợi ý.</p></div></div>
      <p className="analytics-caption">Hồ sơ demo lưu localStorage. Thao tác Đã xem chưa tạo vector ALS mới hoặc cập nhật mô hình đã train.</p>
    </Panel>
  </div>;
}

export default function BigDataAnalytics() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [tab, setTab] = useState<Tab>("data");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const tabId = useId();
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    getAnalytics(controller.signal).then(setData).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Không thể tải số liệu phân tích."); });
    return () => controller.abort();
  }, [retry]);

  function download() {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "cine32-bigdata-analytics.json"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section id="analytics" className="analytics-page" aria-labelledby="analytics-title">
    <div className="analytics-page-heading"><div><span className="section-eyebrow">CINE32 DATA EXPLORER</span><h1 id="analytics-title">Phân tích <span>Big Data</span></h1><p>Khám phá dữ liệu, xem kết quả thực nghiệm và hiểu cách hệ thống tạo gợi ý phim.</p></div><button type="button" className="analytics-download" onClick={download} disabled={!data}>↓ Tải số liệu JSON</button></div>
    {error ? <div className="error-panel" role="alert">{error} <button type="button" onClick={() => setRetry(value => value + 1)}>Thử lại</button></div> : !data ? <div className="analytics-loading" role="status"><div className="loading-line" />Đang tải số liệu Big Data…</div> : <>
      <p className="analytics-snapshot"><span />Kết quả thực nghiệm đã lưu <span className="analytics-snapshot-detail">ALS {date(data.snapshot.trainingDate)} · Benchmark {date(data.snapshot.benchmarkDate)} · HDFS {date(data.snapshot.hdfsDate)}</span></p>
      <div className="analytics-kpis">{[
        [number.format(data.dataset.ratings), "Lượt đánh giá", "Toàn bộ dữ liệu nguồn"],
        [number.format(data.dataset.users), "Người dùng MovieLens", "Mã người chấm ẩn danh"],
        [number.format(data.dataset.movies), "Phim trong danh mục", "Gồm phim chưa có rating"],
        [decimal(data.model.test.rmse, 4), "RMSE test của ALS", "Sai số rating, thấp hơn tốt hơn"],
      ].map(([value, label, note]) => <div key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
      <div className="analytics-tabs" role="tablist" aria-label="Nội dung phân tích Big Data">{tabs.map(item => <button key={item.id} type="button" id={`${tabId}-${item.id}`} role="tab" aria-selected={tab === item.id} aria-controls={`${tabId}-panel-${item.id}`} tabIndex={tab === item.id ? 0 : -1} onClick={() => setTab(item.id)} onKeyDown={event => {
        const index = tabs.findIndex(item => item.id === tab);
        const next = event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
        if (next >= 0) { event.preventDefault(); setTab(tabs[next].id); document.getElementById(`${tabId}-${tabs[next].id}`)?.focus(); }
      }}>{item.label}</button>)}</div>
      <div role="tabpanel" id={`${tabId}-panel-${tab}`} aria-labelledby={`${tabId}-${tab}`} tabIndex={0}>
        {tab === "data" && <DatasetView data={data} />}{tab === "performance" && <PerformanceView data={data} />}{tab === "model" && <ModelView data={data} />}{tab === "pipeline" && <PipelineView data={data} />}
      </div>
      <details className="analytics-sources"><summary>Nguồn số liệu và phạm vi phân tích</summary><p>Đây là ảnh chụp kết quả xử lý offline, không phải dashboard đo truy cập hiện tại, log xem phim hay giám sát HDFS trực tiếp. Chọn một nguồn để đối chiếu với bảng thực nghiệm trong repository.</p><ul>{data.sources.map(source => <li key={source.path}><a href={`https://github.com/Sang6215/movielens-32m-movie-recommender/blob/main/${source.path}`} target="_blank" rel="noopener noreferrer">{source.label} ↗</a></li>)}</ul></details>
    </>}
  </section>;
}
