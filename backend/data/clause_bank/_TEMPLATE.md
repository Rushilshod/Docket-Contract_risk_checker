# Clause bank file naming

One file per supported jurisdiction x domain combo, same naming as
checklists/: india__nda_service.json, uk__rental_tenancy.json, etc.

Suggested shape:
{
  "clauses": [
    {
      "clause_type": "Confidentiality",
      "template": "Each party agrees to keep {other_party}'s confidential information..."
    }
  ]
}

TODO(human) — Section 7, item 1 + item 6: every clause here is text a
real person may sign. It needs the same legal review as the graph edges,
plus user-testing of the "have a lawyer review" prompt's visibility
before anyone outside your testing group uses the drafting feature.
