// PMF Engine: record an interview; raw text is stored verbatim (D-020); conducted_at <= now + 5 minutes (U14)
query "customers/{customer_id}/interviews" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create an interview"
  input {
    int customer_id
    timestamp conducted_at
    text? notes? {
      sensitive = true
    }

    text? transcript? {
      sensitive = true
    }

    text? existing_alternatives? {
      sensitive = true
    }

    text? problem_context? {
      sensitive = true
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/customer" {
      input = {customer_id: $input.customer_id, auth_id: $auth.id}
    } as $access

    precondition ($input.conducted_at <= (now|transform_timestamp:"+5 minutes")) {
      error_type = "inputerror"
      error = "INVALID_TIMESTAMP: conducted_at must not be in the future"
    }

    function.run "pmf/util/patch_data" {
      input = {
        values: {notes: $input.notes, transcript: $input.transcript, existing_alternatives: $input.existing_alternatives, problem_context: $input.problem_context}
        touch : false
      }
    } as $data

    db.add interviews {
      data = {
        customer_id          : $input.customer_id
        conducted_at         : $input.conducted_at
        notes                : $data|get:"notes"
        transcript           : $data|get:"transcript"
        existing_alternatives: $data|get:"existing_alternatives"
        problem_context      : $data|get:"problem_context"
      }
    } as $interview
  }

  response = $interview
}
