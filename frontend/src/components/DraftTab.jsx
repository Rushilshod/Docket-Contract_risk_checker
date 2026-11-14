import { useState } from "react"
import { JURISDICTIONS, DOMAINS, INTERVIEW_FIELDS, isSupported } from "../data/realOptions"
import { runDraft } from "../api/client"
import PipelineStatus from "./PipelineStatus"
import ResultView from "./ResultView"

export default function DraftTab() {
  const [jurisdiction, setJurisdiction] = useState("India")
  const [domain, setDomain] = useState("NDA / Service Agreement")
  const [answers, setAnswers] = useState({})
  const [status, setStatus] = useState("idle")
  const [step, setStep] = useState(0)
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState("")

  const supported = isSupported(jurisdiction, domain)
  const fields = INTERVIEW_FIELDS[domain] || []

  function setAnswer(id, value) {
    setAnswers((a) => ({ ...a, [id]: value }))
  }

  async function handleGenerate() {
    setErrorMessage("")
    setStatus("running")
    setResult(null)

    try {
      const r = await runDraft({ jurisdiction, domain, answers, onStep: setStep })
      setResult(r)
      setStatus("done")
    } catch (error) {
      console.error("Draft flow failed:", error)
      setStatus("idle")
      setStep(0)
      setErrorMessage(error?.message || "The draft generation failed. Please try again.")
    }
  }

  const highFlagCount = result?.report?.summary?.high ?? 0

  return (
    <div>
      <div className="field-row">
        <div>
          <label className="field-label">Jurisdiction</label>
          <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
            {JURISDICTIONS.map((j) => (
              <option key={j}>{j}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label">Contract type</label>
          <select value={domain} onChange={(e) => setDomain(e.target.value)}>
            {DOMAINS.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      {!supported ? (
        <div className="unsupported-box">
          {domain} drafting is not yet supported for {jurisdiction}.
        </div>
      ) : (
        <>
          <div className="field-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {fields.map((f) => (
              <div key={f.id}>
                <label className="field-label">{f.label}</label>
                {f.type === "select" ? (
                  <select value={answers[f.id] || ""} onChange={(e) => setAnswer(f.id, e.target.value)}>
                    <option value="" disabled>
                      Choose…
                    </option>
                    {f.options.map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={answers[f.id] || ""}
                    onChange={(e) => setAnswer(f.id, e.target.value)}
                  />
                )}
              </div>
            ))}
          </div>

          <button className="primary-btn" onClick={handleGenerate} disabled={status === "running"}>
            {status === "running" ? "Assembling & checking draft…" : "Generate draft"}
          </button>

          {errorMessage && <div className="unsupported-box">{errorMessage}</div>}
          {status === "running" && <PipelineStatus activeStep={step} />}
        </>
      )}

      {status === "done" && result && (
        <div style={{ marginTop: 32 }}>
          <div style={{ marginBottom: 28 }}>
            <label className="field-label">Assembled draft (sample text)</label>
            <textarea readOnly rows={7} value={result.draftText} />
          </div>

          <ResultView
            report={result.report}
            footer={
              <div className="lawyer-banner">
                <div>
                  <strong>Have a lawyer review this draft before you sign it.</strong>
                  <p>
                    {highFlagCount > 0
                      ? `This draft still has ${highFlagCount} high-confidence risk flag(s) above — resolve or discuss these before download.`
                      : "No high-confidence risk flags remain, but this is still not a substitute for legal advice."}
                  </p>
                </div>
                <button className="ghost-btn">Download draft (.docx)</button>
              </div>
            }
          />
        </div>
      )}
    </div>
  )
}
