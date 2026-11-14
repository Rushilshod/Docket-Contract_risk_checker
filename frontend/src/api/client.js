import { isSupported } from "../data/realOptions"

export const PIPELINE_STEPS = [
  "Ingesting & segmenting document",
  "Classifying clauses (jurisdiction + deal type)",
  "Checking against missing-clause checklist",
  "Retrieving grounded statute passages",
  "Scoring risk & assembling explanation",
]

function normalizeJurisdictionName(value) {
  const map = {
    India: "india",
    "United Kingdom": "uk",
    "United States": "us",
  }
  return map[value] ?? value.toLowerCase()
}

function normalizeDomainName(value) {
  const normalized = value
    .toLowerCase()
    .replace(/\s*\/\s*/g, "_")
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "")

  const map = {
    nda_service_agreement: "nda_service",
    rental_tenancy_agreement: "rental_tenancy",
  }

  return map[normalized] ?? normalized
}

function updateStep(onStep, index) {
  onStep?.(index)
}

const API_BASE_URL = "http://127.0.0.1:8000"

export async function runCheck({ jurisdiction, domain, file, onStep }) {
  if (!isSupported(jurisdiction, domain)) {
    throw new Error("UNSUPPORTED_COMBINATION")
  }
  if (!file) {
    throw new Error("FILE_REQUIRED")
  }

  const formData = new FormData()
  formData.append("jurisdiction", normalizeJurisdictionName(jurisdiction))
  formData.append("domain", normalizeDomainName(domain))
  formData.append("file", file)

  for (let i = 0; i < PIPELINE_STEPS.length; i++) {
    updateStep(onStep, i)
    await new Promise((resolve) => setTimeout(resolve, 220))
  }

  const response = await fetch(`${API_BASE_URL}/api/check`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "API_ERROR" }))
    throw new Error(error.detail || "API_ERROR")
  }

  return response.json()
}

export async function runDraft({ jurisdiction, domain, answers, onStep }) {
  if (!isSupported(jurisdiction, domain)) {
    throw new Error("UNSUPPORTED_COMBINATION")
  }

  for (let i = 0; i < PIPELINE_STEPS.length; i++) {
    updateStep(onStep, i)
    await new Promise((resolve) => setTimeout(resolve, 200))
  }

  const response = await fetch(`${API_BASE_URL}/api/draft`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jurisdiction: normalizeJurisdictionName(jurisdiction),
      domain: normalizeDomainName(domain),
      answers,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "API_ERROR" }))
    throw new Error(error.detail || "API_ERROR")
  }

  return response.json()
}
