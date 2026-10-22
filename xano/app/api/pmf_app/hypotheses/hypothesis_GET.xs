// PMF Engine: hypothesis detail with its insight and full experiment history
query "hypotheses/{hypothesis_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get a hypothesis with experiments"
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

    db.query experiments {
      where = $db.experiments.hypothesis_id == $input.hypothesis_id
      sort = {created_at: "asc"}
      return = {type: "list"}
    } as $experiments

    var $insight_summary {
      value = {id: $access.insight.id, statement: $access.insight.statement, type: $access.insight.type, review_status: $access.insight.review_status}
    }

    var $out {
      value = $access.record|set:"insight":($insight_summary)
    }

    var.update $out {
      value = $out|set:"experiments":($experiments)
    }
  }

  response = $out
}
