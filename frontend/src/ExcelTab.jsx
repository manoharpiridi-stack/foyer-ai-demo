import { useEffect, useState } from "react";
import { getJSON, postJSON } from "./api.js";
import { addToHistory, clearHistory, loadHistory } from "./history.js";
import Recent from "./Recent.jsx";
import Steps from "./Steps.jsx";

const HISTORY_KEY = "foyer-demo.excel-history";

const ROUTES = {
  sql: {
    label: "Text-to-SQL",
    why: "The question needs exact numbers or filters, so the LLM wrote a SQL query and DuckDB ran it over all rows.",
  },
  semantic: {
    label: "Similarity search",
    why: "The question is about meaning, not exact values, so Chroma returned the claims whose description is closest to the search text. This is a sample of the most similar claims, not a complete count.",
  },
};

export default function ExcelTab() {
  const [info, setInfo] = useState(null);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState(() => loadHistory(HISTORY_KEY));

  useEffect(() => {
    getJSON("/api/excel/info").then(setInfo).catch((e) => setError(e.message));
  }, []);

  async function ask(text) {
    if (!text.trim()) return;
    setQuestion(text);
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const reply = await postJSON("/api/excel/ask", { question: text });
      setResult(reply);
      setHistory(addToHistory(HISTORY_KEY, history, { question: text, time: Date.now(), reply }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="excel">
      <aside className="panel">
        <h2>The dataset</h2>
        {info && (
          <>
            <p className="muted">
              Synthetic insurance claims, {info.rows.toLocaleString("en-US")} rows, Luxembourg, 2022 to 2025.
            </p>
            <a className="button secondary" href="/api/excel/download">
              Download claims.xlsx (raw)
            </a>
            <h3>Cleaned before loading</h3>
            <p className="muted small">
              {info.quality.rows_read.toLocaleString("en-US")} rows read, {info.quality.rows_kept.toLocaleString("en-US")} kept
            </p>
            <ul className="quality">
              {info.quality.fixes
                .filter((fix) => fix.rows > 0)
                .map((fix) => (
                  <li key={fix.issue}>
                    <strong>{fix.rows.toLocaleString("en-US")}</strong>
                    <span>
                      {fix.issue} → {fix.fix.toLowerCase()}
                    </span>
                  </li>
                ))}
            </ul>
            <h3>Columns</h3>
            <ul className="columns">
              {info.columns.map((c) => (
                <li key={c.name}>
                  <code>{c.name}</code>
                  <span>{c.type.toLowerCase()}</span>
                </li>
              ))}
            </ul>
            <h3>Try a question</h3>
            <div className="examples">
              {info.examples.map((q) => (
                <button key={q} className="example" onClick={() => ask(q)} disabled={loading}>
                  {q}
                </button>
              ))}
            </div>
          </>
        )}
      </aside>

      <section className="content">
        <form
          className="ask"
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask anything about the claims…"
          />
          <button className="button" disabled={loading}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
        <p className="privacy">Questions are logged to monitor and improve this demo.</p>

        {error && <p className="error">{error}</p>}
        {!result && !loading && !error && (
          <div className="empty">
            <p>
              Questions that need numbers are turned into SQL. Questions about similar situations use vector search
              over one embedding per row. Every answer shows how it was produced.
            </p>
          </div>
        )}

        {result && (
          <>
            <div className="card answer">
              <span className={`badge ${result.route}`}>{ROUTES[result.route]?.label}</span>
              <p>{result.answer}</p>
            </div>

            <div className="card">
              <h3>How I answered</h3>
              <p className="muted">{ROUTES[result.route]?.why}</p>
              {result.route === "sql" ? (
                <pre className="code">{result.sql}</pre>
              ) : (
                <pre className="code">
                  {`search:  "${result.search}"\nfilters: ${JSON.stringify(result.filters || {})}`}
                </pre>
              )}
              <Steps steps={result.steps} />
            </div>

            <div className="card">
              <h3>
                Result <span className="muted">({result.rows.length} rows shown)</span>
              </h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {result.columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j}>{formatCell(cell)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>

      <aside className="panel recent-panel">
        <Recent
          items={history}
          active={result && question}
          meta={(item) => ({ label: ROUTES[item.reply.route]?.label || item.reply.route, tone: item.reply.route })}
          onSelect={(item) => {
            // Shows the saved answer: no new OpenAI call.
            setQuestion(item.question);
            setResult(item.reply);
            setError("");
          }}
          onClear={() => setHistory(clearHistory(HISTORY_KEY))}
          emptyText="Your questions will appear here. Click one to see its answer again instantly."
        />
      </aside>
    </div>
  );
}

function formatCell(value) {
  if (value === null) return "—";
  if (typeof value === "number" && !Number.isInteger(value)) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return String(value);
}
