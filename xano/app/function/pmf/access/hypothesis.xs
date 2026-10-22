// PMF Engine: load a hypothesis whose insight's product is owned by the caller, or 404
function "pmf/access/hypothesis" {
  description = "Load an owned hypothesis"
  input {
    int hypothesis_id
    int auth_id
  }

  stack {
    db.get hypotheses {
      field_name = "id"
      field_value = $input.hypothesis_id
    } as $hypothesis

    precondition ($hypothesis != null) {
      error_type = "notfound"
      error = "NOT_FOUND: hypothesis not found"
    }

    function.run "pmf/access/insight" {
      input = {insight_id: $hypothesis.insight_id, auth_id: $input.auth_id}
    } as $insight
  }

  response = {record: $hypothesis, insight: $insight.record, product_id: $insight.product_id}
  guid = "1A21fJJZ6TCW0VijX2DwJHBNY3Y"
}
