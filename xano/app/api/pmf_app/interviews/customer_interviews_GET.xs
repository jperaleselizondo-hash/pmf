// PMF Engine: a customer's interviews as summaries (raw text only on the detail endpoint)
query "customers/{customer_id}/interviews" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List interviews of a customer"
  input {
    int customer_id
    int page?=1 filters=min:1
    int per_page?=25 filters=min:1|max:100
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/customer" {
      input = {customer_id: $input.customer_id, auth_id: $auth.id}
    } as $access

    db.query interviews {
      where = $db.interviews.customer_id == $input.customer_id
      sort = {conducted_at: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $page

    var $items {
      value = []
    }

    foreach ($page.items) {
      each as $interview {
        db.query insight_evidence {
          where = $db.insight_evidence.interview_id == $interview.id
          return = {type: "count"}
        } as $evidence_count

        var.update $items {
          value = $items|push:{id: $interview.id, customer_id: $interview.customer_id, conducted_at: $interview.conducted_at, has_notes: $interview.notes != null, has_transcript: $interview.transcript != null, has_existing_alternatives: $interview.existing_alternatives != null, has_problem_context: $interview.problem_context != null, evidence_count: $evidence_count, created_at: $interview.created_at}
        }
      }
    }
  }

  response = $page|set:"items":$items
  guid = "SvkYhcy5VEwQ3-bP7WKYI2xr1hA"
}
