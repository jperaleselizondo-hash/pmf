// PMF Engine: delete a hypothesis only when it has no experiments
query "hypotheses/{hypothesis_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete a hypothesis without experiments"
  input {
    int hypothesis_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/hypothesis" {
      input = {hypothesis_id: $input.hypothesis_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.record.insight_id}
        } as $insight

        function.run "pmf/guard/count_references" {
          input = {entity: "hypothesis", id: $input.hypothesis_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the hypothesis has experiments"
        }

        db.del hypotheses {
          field_name = "id"
          field_value = $input.hypothesis_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.hypothesis_id}
  guid = "v8C2QEAWE_RSX1-W_8oLzXVZRr8"
}
