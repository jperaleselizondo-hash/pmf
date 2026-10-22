// PMF Engine: serialize writes on one insight and its evidence/hypothesis family (PROVISIONAL, U13)
// Call first inside db.transaction; proven only after isolated concurrency tests C02/C04 pass.
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
