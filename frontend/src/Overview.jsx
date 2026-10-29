// Scores from eval/results.md; update them after re-running scripts/evaluate.py.
const STATS = [
  ["100,000", "claims queried"],
  ["295", "guide passages"],
  ["37", "test questions"],
  ["~3 s", "per answer"],
];

// Real result of "How many claims were rejected in 2024, by product?"
const REJECTED_2024 = [
  ["Motor", 2556],
  ["Home", 2041],
  ["Liability", 918],
];

const LESSONS = [
  ["Counting needs SQL", "Top-k retrieval sees 20 rows, not 100,000. Vector search is kept for what it is good at: matching meaning."],
  ["One green run proves little", "Re-running the same evaluation exposed three prompt gaps (SQL dialect, inferred filters, vague questions). Each is fixed."],
  ["Measure in production", "A cold first visit on AWS took up to 45 s. Logs and browser timings showed two causes: Lambda's 10 s start-up limit, and parallel requests each starting a new copy. Fixed, it now takes about 5 s, and about 2 s when warm."],
];

const LIMITS = [
  "The claims data is synthetic, so similarity results repeat descriptions.",
  "The 37 test questions are mine; real user questions would be the next step.",
  "The guide content is the public site's information pages and FAQ, not its simulators or maps.",
];

const STACK = ["FastAPI", "React", "DuckDB", "Chroma", "OpenAI", "Docker", "AWS Lambda", "Terraform"];

function ExcelPreview() {
  const max = Math.max(...REJECTED_2024.map(([, n]) => n));
  return (
    <div className="preview">
      <code className="preview-sql">
        SELECT product, count(*) FROM claims WHERE status = 'Rejected' AND year(claim_date) = 2024 GROUP BY product
      </code>
      <p className="preview-label">Rejected claims in 2024</p>
      {REJECTED_2024.map(([label, n], i) => (
        <div key={label} className="bar-row">
          <span>{label}</span>
          <div className="bar-track">
            <div className="bar" style={{ width: `${(n / max) * 100}%`, animationDelay: `${0.3 + i * 0.15}s` }} />
          </div>
          <strong>{n.toLocaleString("en-US")}</strong>
        </div>
      ))}
    </div>
  );
}

function GuidePreview() {
  return (
    <div className="preview">
      <div className="mini-msg user">Do I need to exchange my EU driving licence?</div>
      <div className="mini-msg bot">
        No. An EU licence stays valid in Luxembourg with no time limit.
        <span className="mini-chip">Permis de conduire · permis-1</span>
      </div>
      <div className="mini-passage">
        « Un permis délivré par un État de l'Espace économique européen reste valable au Luxembourg, sans limitation
        de durée. »
      </div>
    </div>
  );
}

const EXERCISES = [
  {
    tab: "excel",
    number: "Exercise 2",
    title: "RAG on a 100,000-row Excel file",
    asked: "You are given an Excel file with 100,000 rows. Which RAG method would you use?",
    approach: [
      "Messy file cleaned first: every fix counted and shown",
      "Counts, totals and filters → SQL over all rows in DuckDB",
      "Situations described in words → vector search, one embedding per row",
      "Every answer shows its SQL or search",
    ],
    score: "20/20",
    scoreDetail: "naive top-20 RAG scores 4/20",
    cta: "Ask the Excel file",
    Preview: ExcelPreview,
  },
  {
    tab: "guide",
    number: "Exercise 3",
    title: "A chatbot for newcomers to Luxembourg",
    asked: "Recognise the page being read, open the right page, highlight the passage.",
    approach: [
      "Searches the current page first, then the whole guide",
      "Answers only from cited passages, checked in code",
      "Opens the page and highlights the evidence, in French or English",
      "Adapts to the reader: EU or non-EU citizen, with a car, with family",
    ],
    score: "17/17",
    scoreDetail: "including 3 out-of-scope questions declined",
    cta: "Open the guide chatbot",
    Preview: GuidePreview,
  },
];

export default function Overview({ onOpen }) {
  return (
    <div className="overview">
      <section className="hero">
        <div className="aurora" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="hero-content">
          <span className="live-pill">
            <i /> Live on AWS · Frankfurt
          </span>
          <p className="hero-kicker">Foyer AI recruitment · exercises 2 and 3</p>
          <h2>
            Ask <span className="grad">100,000 claims</span> and a <span className="grad">newcomer guide</span>, and see
            exactly how every answer was found.
          </h2>
          <p className="lead">
            Each answer shows the SQL or search used, the passages cited and the time each step took. When the evidence
            is missing, the tools say so instead of guessing.
          </p>
          <div className="hero-actions">
            <button className="button" onClick={() => onOpen("excel")}>
              Try the Excel RAG →
            </button>
            <button className="button ghost" onClick={() => onOpen("guide")}>
              Try the guide chatbot →
            </button>
          </div>
          <div className="stats">
            {STATS.map(([value, label]) => (
              <div key={label} className="stat">
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="exercise-grid">
        {EXERCISES.map(({ Preview, ...ex }) => (
          <article key={ex.tab} className={`exercise ex-${ex.tab}`}>
            <div className="exercise-top">
              <p className="eyebrow">{ex.number}</p>
              <span className="score-pill">
                <strong>{ex.score}</strong> {ex.scoreDetail}
              </span>
            </div>
            <h3>{ex.title}</h3>
            <p className="asked">“{ex.asked}”</p>
            <Preview />
            <ul className="approach">
              {ex.approach.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <button className="button tone" onClick={() => onOpen(ex.tab)}>
              {ex.cta} →
            </button>
          </article>
        ))}
      </section>

      <section className="glass flow-card">
        <h3>How it works</h3>
        <div className="flow">
          <div className="node">React app</div>
          <div className="wire" />
          <div className="node accent">FastAPI</div>
          <div className="wire" />
          <div className="stack">
            <div className="node db">
              <strong>DuckDB</strong>
              <span>100,000 claims, read-only SQL</span>
            </div>
            <div className="node vec">
              <strong>Chroma</strong>
              <span>row vectors + 295 guide passages</span>
            </div>
            <div className="node llm">
              <strong>OpenAI</strong>
              <span>gpt-4.1-mini, embeddings</span>
            </div>
          </div>
        </div>
        <p className="flow-note">
          One Docker image on AWS Lambda in Frankfurt: ECR, a Function URL and a keep-warm schedule, all defined in
          Terraform. The same image runs on a laptop.
        </p>
      </section>

      <section className="two-col">
        <div className="glass">
          <h3>What I learned building it</h3>
          <ol className="timeline">
            {LESSONS.map(([title, text]) => (
              <li key={title}>
                <strong>{title}</strong>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </div>
        <div className="glass limits-card">
          <h3>Limits, stated up front</h3>
          <ul className="limits">
            {LIMITS.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="stack-pills">
        {STACK.map((name) => (
          <span key={name}>{name}</span>
        ))}
      </footer>
    </div>
  );
}
