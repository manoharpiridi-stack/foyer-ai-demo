export default function Steps({ steps }) {
  const total = steps.reduce((sum, s) => sum + s.ms, 0);
  return (
    <ol className="steps">
      {steps.map((s, i) => (
        <li key={i}>
          <span className="step-name">{s.name}</span>
          {s.detail && <span className="step-detail">{s.detail}</span>}
          <span className="step-ms">{s.ms} ms</span>
        </li>
      ))}
      <li className="total">
        <span className="step-name">Total</span>
        <span className="step-ms">{total} ms</span>
      </li>
    </ol>
  );
}
