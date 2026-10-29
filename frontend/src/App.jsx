import { useState } from "react";
import ExcelTab from "./ExcelTab.jsx";
import GuideTab from "./GuideTab.jsx";
import Overview from "./Overview.jsx";

const TABS = [
  { id: "overview", label: "Overview", hint: "Start here" },
  { id: "excel", label: "Ask a 100,000-row Excel file", hint: "Exercise 2" },
  { id: "guide", label: "Luxembourg newcomer guide chatbot", hint: "Exercise 3" },
];

export default function App() {
  const [tab, setTab] = useState("overview");

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">AI</span>
          <div>
            <h1>Insurance AI demo</h1>
            <p>Two small, working answers to the Foyer AI recruitment exercises</p>
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
              <small>{t.hint}</small>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "overview" && <Overview onOpen={setTab} />}
        {tab === "excel" && <ExcelTab />}
        {tab === "guide" && <GuideTab />}
      </main>
    </div>
  );
}
