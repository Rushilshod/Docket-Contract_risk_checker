import { useState } from "react"
import CheckTab from "./components/CheckTab"
import DraftTab from "./components/DraftTab"

export default function App() {
  const [tab, setTab] = useState("check")

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <h1>Docket</h1>
          <p className="subtitle">
            Cross-jurisdictional contract risk checker & drafting assistant —
            India, UK, US.
          </p>
        </div>
      </header>

      <div className="tab-row">
        <button
          className={`tab-btn ${tab === "check" ? "active" : ""}`}
          onClick={() => setTab("check")}
        >
          Check a contract
        </button>
        <button
          className={`tab-btn ${tab === "draft" ? "active" : ""}`}
          onClick={() => setTab("draft")}
        >
          Draft a contract
        </button>
      </div>

      <div className="tab-panel">
        {tab === "check" ? <CheckTab /> : <DraftTab />}
      </div>
    </div>
  )
}
