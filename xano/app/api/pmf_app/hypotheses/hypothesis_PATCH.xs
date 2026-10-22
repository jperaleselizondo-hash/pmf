// PMF Engine: update a hypothesis; status transitions are validated against experiments (U7, R3.1)
query "hypotheses/{hypothesis_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update a hypothesis"
  input {
    int hypothesis_id
    text? statement? filters=trim
    text? expected_outcome? filters=trim
    text? success_metric? filters=trim
    enum? priority? {
      values = ["low", "medium", "high"]
    }

    enum? status? {
      values = ["proposed", "testing", "validated", "rejected"]
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/hypothesis" {
      input = {hypothesis_id: $input.hypothesis_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values  : {statement: $input.statement, expected_outcome: $input.expected_outcome, success_metric: $input.success_metric, priority: $input.priority, status: $input.status}
        required: ["statement", "expected_outcome", "success_metric"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.record.insight_id}
        } as $insight

        db.get hypotheses {
          field_name = "id"
          field_value = $input.hypothesis_id
        } as $current

        conditional {
          if ($input.status != null && $input.status != $current.status) {
            db.query experiments {
              where = $db.experiments.hypothesis_id == $input.hypothesis_id
              return = {type: "list"}
              output = ["id", "conclusion"]
            } as $experiments

            function.run "pmf/validation/validate_hypothesis_status" {
              input = {current: $current.status, next: $input.status, experiments: $experiments}
            } as $transition
          }
        }

        db.patch hypotheses {
          field_name = "id"
          field_value = $input.hypothesis_id
          data = $data
        } as $updated
      }
    }
  }

  response = $updated
}
