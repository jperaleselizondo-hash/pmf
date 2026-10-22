// PMF Engine: load an experiment whose hypothesis chain is owned by the caller, or 404
function "pmf/access/experiment" {
  description = "Load an owned experiment"
  input {
    int experiment_id
    int auth_id
  }

  stack {
    db.get experiments {
      field_name = "id"
      field_value = $input.experiment_id
    } as $experiment

    precondition ($experiment != null) {
      error_type = "notfound"
      error = "NOT_FOUND: experiment not found"
    }

    function.run "pmf/access/hypothesis" {
      input = {hypothesis_id: $experiment.hypothesis_id, auth_id: $input.auth_id}
    } as $hypothesis
  }

  response = {record: $experiment, hypothesis: $hypothesis.record, insight: $hypothesis.insight, product_id: $hypothesis.product_id}
  guid = "A0gJI3a4ez66PxQLAjslTtMlfls"
}
