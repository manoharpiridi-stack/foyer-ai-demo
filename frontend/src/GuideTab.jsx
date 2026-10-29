import { useEffect, useRef, useState } from "react";
import { getJSON, postJSON } from "./api.js";
import { addToHistory, clearHistory, loadHistory } from "./history.js";
import Recent from "./Recent.jsx";
import Steps from "./Steps.jsx";

const HISTORY_KEY = "foyer-demo.guide-history";

const EXAMPLES = [
  "Combien de jours ai-je pour déclarer mon arrivée à la commune ?",
  "Do I need to exchange my EU driving licence?",
  "Mon assurance habitation couvre-t-elle la responsabilité civile ?",
  "How much are family allowances per child?",
];

// The source data stores categories as ids without accents.
const CATEGORY_LABELS = {
  fr: { Sante: "Santé", Mobilite: "Mobilité", Impots: "Impôts" },
  en: {
    Administratif: "Administration", Sante: "Health", Logement: "Housing", Impots: "Taxes", Quotidien: "Daily life",
    Travail: "Work", Famille: "Family", Mobilite: "Mobility", Finances: "Money",
  },
};

export default function GuideTab() {
  const [lang, setLang] = useState("fr");
  const [pages, setPages] = useState([]);
  const [page, setPage] = useState(null);
  const [highlight, setHighlight] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(() => loadHistory(HISTORY_KEY));
  const [profile, setProfile] = useState({ citizenship: null, car: false, family: false });
  const readerRef = useRef(null);
  const chatRef = useRef(null);
  const label = (cat) => CATEGORY_LABELS[lang][cat] || cat;

  // Passage ids are the same in both languages, so switching keeps the page and its highlights.
  // The two requests run one after the other: in parallel, the second would cold-start another Lambda copy.
  useEffect(() => {
    getJSON(`/api/guide/pages?lang=${lang}`).then((list) => {
      setPages(list);
      return openPage(page?.id || "arrivee", highlight, lang);
    });
  }, [lang]);

  useEffect(() => {
    const first = highlight.length && readerRef.current?.querySelector(`[data-pid="${highlight[0]}"]`);
    if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
    else readerRef.current?.scrollTo({ top: 0 });
  }, [page, highlight]);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function openPage(id, passageIds = [], language = lang) {
    if (page?.id !== id || page?.lang !== language) {
      setPage({ ...(await getJSON(`/api/guide/pages/${id}?lang=${language}`)), lang: language });
    }
    setHighlight(passageIds);
  }

  async function ask(text) {
    if (!text.trim() || loading) return;
    const conversation = messages.map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: text }]);
    setQuestion("");
    setLoading(true);
    try {
      const reply = await postJSON("/api/guide/ask", { question: text, page_id: page?.id, history: conversation, profile });
      setMessages((m) => [...m, { role: "assistant", content: reply.answer, reply }]);
      const { found, page_id, passage_ids } = reply;
      setHistory(addToHistory(HISTORY_KEY, history, { question: text, time: Date.now(), found, page_id, passage_ids }));
      if (found) await openPage(page_id, passage_ids);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  const categories = [...new Set(pages.map((p) => p.category))];

  return (
    <div className="guide">
      <aside className="panel nav">
        {history.length > 0 && (
          <Recent
            items={history}
            meta={(item) =>
              item.found
                ? { label: pages.find((p) => p.id === item.page_id)?.title || item.page_id, tone: "semantic" }
                : { label: "not covered", tone: "none" }
            }
            onSelect={(item) => item.found && openPage(item.page_id, item.passage_ids)}
            onClear={() => setHistory(clearHistory(HISTORY_KEY))}
          />
        )}
        {categories.map((cat) => (
          <div key={cat}>
            <h4>{label(cat)}</h4>
            {pages
              .filter((p) => p.category === cat)
              .map((p) => (
                <button
                  key={p.id}
                  className={page?.id === p.id ? "nav-item active" : "nav-item"}
                  onClick={() => openPage(p.id)}
                >
                  {p.title}
                </button>
              ))}
          </div>
        ))}
      </aside>

      <article className="panel reader" ref={readerRef}>
        <div className="lang-switch" role="group" aria-label="Page language">
          {["fr", "en"].map((l) => (
            <button key={l} className={lang === l ? "active" : ""} onClick={() => setLang(l)}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        {page && (
          <>
            {lang === "en" && (
              <p className="translated">Automatically translated from French. The French original is the reference.</p>
            )}
            <p className="eyebrow">{label(page.category)}</p>
            <h2>{page.title}</h2>
            <p className="summary">{page.summary}</p>
            {page.blocks.map((b, i) => (
              <Block key={b.id || i} block={b} highlighted={highlight.includes(b.id)} />
            ))}
            {page.sources.length > 0 && (
              <p className="muted small">
                Official sources:{" "}
                {page.sources.map((s, i) => (
                  <a key={i} href={s.url} target="_blank" rel="noreferrer">
                    {s.title}
                    {i < page.sources.length - 1 ? ", " : ""}
                  </a>
                ))}
              </p>
            )}
            <p className="muted small">
              Content from{" "}
              <a href={page.url} target="_blank" rel="noreferrer">
                lux-guide.github.io
              </a>
              , shown here for the demo.
            </p>
          </>
        )}
      </article>

      <section className="panel chat">
        <ProfileBar profile={profile} onChange={setProfile} />
        <div className="messages" ref={chatRef}>
          {messages.length === 0 && (
            <div className="examples">
              <p className="muted">
                Ask in French or English. I answer from the guide, open the page that holds the answer and highlight the
                passage.
              </p>
              {EXAMPLES.map((q) => (
                <button key={q} className="example" onClick={() => ask(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
          {messages.map((m, i) => (
            <ChatMessage key={i} message={m} pages={pages} onOpen={openPage} />
          ))}
          {loading && <div className="msg assistant muted">Searching the guide…</div>}
        </div>
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
            placeholder={page ? `Ask about "${page.title}" or anything else…` : "Ask a question…"}
          />
          <button className="button" disabled={loading}>
            Send
          </button>
        </form>
        <p className="privacy">Questions are logged to monitor and improve this demo.</p>
      </section>
    </div>
  );
}

// The reader's situation, sent with each question so the answer gives the rule that applies to them.
function ProfileBar({ profile, onChange }) {
  function setCitizenship(value) {
    onChange({ ...profile, citizenship: profile.citizenship === value ? null : value });
  }

  function toggle(key) {
    onChange({ ...profile, [key]: !profile[key] });
  }

  return (
    <div className="profile-bar">
      <span className="profile-label">Your situation</span>
      <button className={profile.citizenship === "EU" ? "pill active" : "pill"} onClick={() => setCitizenship("EU")}>
        EU citizen
      </button>
      <button className={profile.citizenship === "non-EU" ? "pill active" : "pill"} onClick={() => setCitizenship("non-EU")}>
        Non-EU citizen
      </button>
      <button className={profile.car ? "pill active" : "pill"} onClick={() => toggle("car")}>
        With a car
      </button>
      <button className={profile.family ? "pill active" : "pill"} onClick={() => toggle("family")}>
        With family
      </button>
    </div>
  );
}

function Block({ block, highlighted }) {
  const cls = highlighted ? "passage highlighted" : "passage";
  if (block.type === "h") return <h3>{block.text}</h3>;
  if (block.type === "faq")
    return (
      <div className={cls} data-pid={block.id}>
        <strong>{block.q}</strong>
        <p>{block.a}</p>
      </div>
    );
  if (block.type === "table")
    return (
      <div className={cls} data-pid={block.id}>
        <strong>{block.title}</strong>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {block.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  return (
    <p className={cls} data-pid={block.id}>
      {block.text}
    </p>
  );
}

function ChatMessage({ message, pages, onOpen }) {
  const { role, content, reply } = message;
  const title = (id) => pages.find((p) => p.id === id)?.title || id;
  return (
    <div className={`msg ${role}`}>
      <p>{content}</p>
      {reply?.opened_other_page && <p className="note">Opened “{title(reply.page_id)}”, where the answer is.</p>}
      {reply?.found === false && <p className="note">No supporting passage found, so no page was opened.</p>}
      {reply?.sources?.length > 0 && (
        <div className="chips">
          {reply.sources.map((s) => (
            <button key={s.id} className="chip" onClick={() => onOpen(s.page_id, [s.id])}>
              {title(s.page_id)} · {s.id}
            </button>
          ))}
        </div>
      )}
      {reply && (
        <details>
          <summary>How I answered</summary>
          <Steps steps={reply.steps} />
          <p className="muted small">Retrieved passages (cited ones are marked):</p>
          <ul className="retrieved">
            {reply.retrieved.map((h) => (
              <li key={h.id} className={reply.sources.some((s) => s.id === h.id) ? "cited" : ""}>
                <code>{h.id}</code> {h.text.slice(0, 140)}…
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
