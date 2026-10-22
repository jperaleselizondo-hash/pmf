// PMF Engine: insight detail with supporting and contradicting evidence (and their original sources) and hypotheses
query "insights/{insight_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get an insight with evidence and hypotheses"
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

    db.query insight_evidence {
      where = $db.insight_evidence.insight_id == $input.insight_id
      sort = {created_at: "asc"}
      return = {type: "list"}
    } as $rows

    var $evidence {
      value = []
    }

    foreach ($rows) {
      each as $row {
        function.run "pmf/evidence/source_summary" {
          input = {evidence: $row}
        } as $source

        var.update $evidence {
          value = $evidence|push:($row|set:"source":$source)
        }
      }
    }

    db.query hypotheses {
      where = $db.hypotheses.insight_id == $input.insight_id
      sort = {created_at: "desc"}
      return = {type: "list"}
      output = ["id", "statement", "status", "priority"]
    } as $hypotheses

    var $out {
      value = $access.record|set:"evidence":($evidence)
    }

    var.update $out {
      value = $out|set:"hypotheses":($hypotheses)
    }
  }

  response = $out
  guid = "3zlUw8RqYmN_mKLUQj8hCRdWC_Y"
}
