export const JURISDICTIONS = ["India", "United Kingdom", "United States"]

export const DOMAINS = ["NDA / Service Agreement", "Rental / Tenancy Agreement"]

export const SUPPORTED_COMBOS = {
  India: ["NDA / Service Agreement", "Rental / Tenancy Agreement"],
  "United Kingdom": ["NDA / Service Agreement", "Rental / Tenancy Agreement"],
  "United States": ["NDA / Service Agreement"],
}

export const STAGES = ["Signing", "Performance", "Termination"]

export function isSupported(jurisdiction, domain) {
  return Boolean(SUPPORTED_COMBOS[jurisdiction]?.includes(domain))
}

export const INTERVIEW_FIELDS = {
  "NDA / Service Agreement": [
    { id: "partyA", label: "Disclosing / hiring party name", type: "text" },
    { id: "partyB", label: "Receiving / service-provider name", type: "text" },
    { id: "term", label: "Initial term (months)", type: "text" },
    { id: "autoRenew", label: "Auto-renew each term?", type: "select", options: ["Yes", "No"] },
    { id: "scope", label: "One-line scope of work / purpose", type: "text" },
  ],
  "Rental / Tenancy Agreement": [
    { id: "landlord", label: "Landlord name", type: "text" },
    { id: "tenant", label: "Tenant name", type: "text" },
    { id: "term", label: "Tenancy length (months)", type: "text" },
    { id: "deposit", label: "Security deposit amount", type: "text" },
    { id: "renewalNotice", label: "Notice period before renewal (days)", type: "text" },
  ],
}
