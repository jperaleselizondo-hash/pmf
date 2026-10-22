// PMF Engine: delete an insight only when it has no evidence and no hypotheses
query "insights/{insight_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an unreferenced insight"
  input {
    int insight_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/insight" {
      input = {insight_id: $input.insight_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $input.insight_id}
        } as $insight

        function.run "pmf/guard/count_references" {
          input = {entity: "insight", id: $input.insight_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the insight has evidence or hypotheses"
        }

        db.del insights {
          field_name = "id"
          field_value = $input.insight_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.insight_id}
}
