import { PIPELINE_STEPS } from "../api/client"

export default function PipelineStatus({ activeStep }) {
  return (
    <div className="pipeline-status">
      {PIPELINE_STEPS.map((step, i) => (
        <div
          key={step}
          className={`step ${i < activeStep ? "done" : i === activeStep ? "active" : ""}`}
        >
          {i < activeStep ? "✓" : i === activeStep ? "…" : "·"} {step}
        </div>
      ))}
    </div>
  )
}
