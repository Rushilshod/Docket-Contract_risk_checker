import { useState } from "react"
import { JURISDICTIONS, DOMAINS, isSupported } from "../data/realOptions"
import { runCheck } from "../api/client"
import PipelineStatus from "./PipelineStatus"
import ResultView from "./ResultView"

export default function CheckTab() {
  const [jurisdiction, setJurisdiction] = useState("India")
  const [domain, setDomain] = useState("NDA / Service Agreement")
  const [fileName, setFileName] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [status, setStatus] = useState("idle") // idle | running | done
  const [step, setStep] = useState(0)
  const [report, setReport] = useState(null)
  const [errorMessage, setErrorMessage] = useState("")

  const supported = isSupported(jurisdiction, domain)

  async function handleRun() {
    if (!selectedFile) {
      setStatus("idle")
      setErrorMessage("Please select a contract file before running the check.")
      return
    }

    setErrorMessage("")
    setStatus("running")
    setReport(null)

    try {
      const r = await runCheck({ jurisdiction, domain, file: selectedFile, onStep: setStep })
      setReport(r)
      setStatus("done")
    } catch (error) {
      console.error("Check flow failed:", error)
      setStatus("idle")
      setStep(0)
      setErrorMessage(error?.message || "The check failed. Please try again.")
    }
  }

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (f) {
      setFileName(f.name)
      setSelectedFile(f)
    }
  }

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
          {domain} is not yet supported for {jurisdiction}. Choose a different
          jurisdiction, or a supported contract type, to continue.
        </div>
      ) : (
        <>
          <div className="upload-zone">
            <p>
              <strong>Upload a contract</strong> to check it — PDF or DOCX.
            </p>
            <input type="file" accept=".pdf,.docx" onChange={handleFile} style={{ marginTop: 10 }} />
            {fileName && <div className="file-chip">📄 {fileName}</div>}
          </div>

          <button className="primary-btn" onClick={handleRun} disabled={status === "running"}>
            {status === "running" ? "Running checks…" : "Run risk check"}
          </button>

          {errorMessage && <div className="unsupported-box">{errorMessage}</div>}
          {status === "running" && <PipelineStatus activeStep={step} />}
        </>
      )}

      {status === "done" && report && (
        <div style={{ marginTop: 32 }}>
          <ResultView
            report={report}
            footer={
              <div className="lawyer-banner">
                <div>
                  <strong>This is not legal advice.</strong>
                  <p>Have a lawyer review this contract before you sign it or rely on it.</p>
                </div>
              </div>
            }
          />
        </div>
      )}
    </div>
  )
}
