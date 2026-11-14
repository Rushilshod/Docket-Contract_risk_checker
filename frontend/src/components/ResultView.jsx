import { useState } from "react"
import { STAGES } from "../data/realOptions"

function Flag({ flag }) {
  const badgeLabel =
    flag.severity === "missing" ? "missing" : flag.severity === "high" ? "high risk" : "medium risk"
  const recommendation = flag.recommendation || flag.explanation || flag.body

  return (
    <div className={`flag ${flag.severity}`}>
      <div className="flag-top">
        <div>
          <div className="flag-title">{flag.title}</div>
        </div>
        <span className={`flag-badge ${flag.severity}`}>{badgeLabel}</span>
      </div>

      <div className="flag-body">{flag.body}</div>

      {recommendation && (
        <div className="flag-recommendation">
          <div className="flag-recommendation-label">Gemini recommendation</div>
          <div className="flag-recommendation-text">{recommendation}</div>
        </div>
      )}

      <div className="flag-meta">
        <span>Clause type: {flag.clauseType}</span>
        {flag.disadvantages && <span>Disadvantages: {flag.disadvantages}</span>}
        {typeof flag.confidence === "number" && (
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            Confidence {Math.round(flag.confidence * 100)}%
            <span className="confidence-bar">
              <span style={{ width: `${flag.confidence * 100}%` }} />
            </span>
          </span>
        )}
      </div>

      {flag.citationLabel && (
        <details className="citation">
          <summary>View retrieved statute passage — {flag.citationLabel}</summary>
          <div className="citation-text">{flag.citationText}</div>
          <div className="sample-note">Sample text for demo layout — not verified statute content.</div>
        </details>
      )}
    </div>
  )
}

export default function ResultView({ report, footer }) {
  const [stage, setStage] = useState(STAGES[0])
  const { summary } = report
  const flags = report.stages[stage] || []

  return (
    <div>
      <div className="result-header">
        <h2>Risk report — {report.domain}</h2>
        <span className="result-meta">
          {report.jurisdiction} · generated {new Date(report.generatedAt).toLocaleString()}
        </span>
      </div>

      <div className="summary-strip">
        <div className="summary-cell risk-high">
          <div className="num">{summary.high}</div>
          <div className="lbl">High-risk flags</div>
        </div>
        <div className="summary-cell risk-med">
          <div className="num">{summary.medium}</div>
          <div className="lbl">Medium-risk flags</div>
        </div>
        <div className="summary-cell">
          <div className="num">{summary.missing}</div>
          <div className="lbl">Missing clauses</div>
        </div>
        <div className="summary-cell risk-ok">
          <div className="num">{summary.ok}</div>
          <div className="lbl">Clauses, no flag</div>
        </div>
      </div>

      <div className="stage-row">
        {STAGES.map((s) => (
          <button
            key={s}
            className={`stage-chip ${stage === s ? "active" : ""}`}
            onClick={() => setStage(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {flags.length === 0 ? (
        <p style={{ color: "var(--ink-soft)", fontSize: 13.5 }}>
          No flags surfaced at this lifecycle stage.
        </p>
      ) : (
        flags.map((f) => <Flag key={f.id} flag={f} />)
      )}

      {footer}
    </div>
  )
}
