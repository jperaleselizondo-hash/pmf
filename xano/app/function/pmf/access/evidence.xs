// PMF Engine: load an evidence link whose insight's product is owned by the caller, or 404
function "pmf/access/evidence" {
  description = "Load an owned evidence link"
  input {
    int evidence_id
    int auth_id
  }

  stack {
    db.get insight_evidence {
      field_name = "id"
      field_value = $input.evidence_id
    } as $evidence

    precondition ($evidence != null) {
      error_type = "notfound"
      error = "NOT_FOUND: evidence not found"
    }

    function.run "pmf/access/insight" {
      input = {insight_id: $evidence.insight_id, auth_id: $input.auth_id}
    } as $insight
  }

  response = {record: $evidence, insight: $insight.record, product_id: $insight.product_id}
}
