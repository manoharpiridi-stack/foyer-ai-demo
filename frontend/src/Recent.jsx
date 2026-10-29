function timeAgo(timestamp) {
  const minutes = Math.round((Date.now() - timestamp) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 24 * 60) return `${Math.round(minutes / 60)} h ago`;
  return new Date(timestamp).toLocaleDateString("en-GB");
}

// items: [{ question, time, ... }]; meta(item) returns { label, tone } shown under each question.
export default function Recent({ items, active, meta, onSelect, onClear, emptyText }) {
  return (
    <div className="recent">
      <div className="recent-head">
        <h3>Recent questions</h3>
        {items.length > 0 && (
          <button className="link-button" onClick={onClear}>
            Clear
          </button>
        )}
      </div>
      {items.length === 0 && emptyText && <p className="muted small">{emptyText}</p>}
      {items.map((item) => {
        const { label, tone } = meta(item);
        return (
          <button
            key={item.question}
            className={item.question === active ? "recent-item active" : "recent-item"}
            onClick={() => onSelect(item)}
          >
            <span className="recent-question">{item.question}</span>
            <span className="recent-meta">
              <i className={`dot ${tone}`} />
              {label} · {timeAgo(item.time)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
