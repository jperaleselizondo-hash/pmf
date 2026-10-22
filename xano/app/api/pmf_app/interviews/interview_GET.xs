// PMF Engine: interview detail with full raw text and the evidence links that cite it
query "interviews/{interview_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get an interview"
  input {
    int interview_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/interview" {
      input = {interview_id: $input.interview_id, auth_id: $auth.id}
    } as $access

    db.query insight_evidence {
      where = $db.insight_evidence.interview_id == $input.interview_id
      sort = {created_at: "desc"}
      return = {type: "list"}
      output = ["id", "insight_id", "relationship", "source_field"]
    } as $evidence

    var $customer_summary {
      value = {id: $access.customer.id, name: $access.customer.name, external_id: $access.customer.external_id}
    }

    var $cited {
      value = ($evidence|count) > 0
    }

    var $out {
      value = $access.record|set:"customer":($customer_summary)
    }

    var.update $out {
      value = $out|set:"evidence":($evidence)
    }

    var.update $out {
      value = $out|set:"cited":($cited)
    }
  }

  response = $out
  guid = "fFO2SMMa9D8slJeRaMbMvakIsbc"
}
