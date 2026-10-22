// PMF Engine: INTENDED serialization point for one insight and its evidence/hypothesis family (UNVERIFIED, U13)
// Called first inside db.transaction. Rewriting an unchanged column is an attempt to take a row lock; it is
// not known to lock anything until the isolated repeated-trial tests C02/C04 pass with concurrent overlap
// AND a negative control (this lock disabled) shows they fail. Any failed invariant blocks deployment.
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
      data = {statement: $insight.statement}
    } as $locked
  }

  response = $locked
}
