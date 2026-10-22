// PMF Engine: create a hypothesis from a reviewed insight; status starts as proposed
query "insights/{insight_id}/hypotheses" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create a hypothesis"
  input {
    int insight_id
    text statement filters=trim
    text expected_outcome filters=trim
    text success_metric filters=trim
    enum? priority? {
      values = ["low", "medium", "high"]
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/insight" {
      input = {insight_id: $input.insight_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values  : {statement: $input.statement, expected_outcome: $input.expected_outcome, success_metric: $input.success_metric}
        required: ["statement", "expected_outcome", "success_metric"]
        touch   : false
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $input.insight_id}
        } as $insight

        function.run "pmf/insight/assert_reviewed" {
          input = {insight: $insight}
        } as $reviewed

        db.add hypotheses {
          data = {
            insight_id      : $input.insight_id
            statement       : $data.statement
            expected_outcome: $data.expected_outcome
            success_metric  : $data.success_metric
            priority        : $input.priority ?? "medium"
            status          : "proposed"
          }
        } as $hypothesis
      }
    }
  }

  response = $hypothesis
}
