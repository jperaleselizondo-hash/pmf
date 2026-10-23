// PMF Engine: serialization point for one insight and its evidence/hypothesis family (U13, PROPOSED FIX)
// Called first inside db.transaction. The live run (2026-10-23) showed that rewriting an unchanged column
// does not serialize (C02 20/25, C04 21/25 violations). This version performs a REAL row change
// (`updated_at = now`), which takes the row lock until commit in a real database transaction. Verified only
// if C02/C04 pass with full overlap and the T01 rollback check passes (rejected request leaves updated_at).
function "pmf/lock/insight" {
  description = "Lock an insight row and return its current state"
  input {
    int insight_id
  }

  stack {
    db.get insights {
      field_name = "id"
      field_value = $input.insight_id
    } as $insight

    precondition ($insight != null) {
      error_type = "notfound"
      error = "NOT_FOUND: insight not found"
    }

    db.edit insights {
      field_name = "id"
      field_value = $input.insight_id
      data = {updated_at: now}
    } as $locked
  }

  response = $locked
  guid = "PIV8HNwZ6PmQsORtg4xNTf-w8ic"
}
