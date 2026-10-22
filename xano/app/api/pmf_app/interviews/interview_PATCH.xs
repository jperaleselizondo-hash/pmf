// PMF Engine: update an interview; raw text is locked once cited by evidence (U4); customer is immutable
query "interviews/{interview_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update an interview"
  input {
    int interview_id
    timestamp? conducted_at?
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

    function.run "pmf/access/interview" {
      input = {interview_id: $input.interview_id, auth_id: $auth.id}
    } as $access

    precondition ($input.conducted_at == null || $input.conducted_at <= (now|transform_timestamp:"+5 minutes")) {
      error_type = "inputerror"
      error = "INVALID_TIMESTAMP: conducted_at must not be in the future"
    }

    function.run "pmf/util/patch_data" {
      input = {
        values: {conducted_at: $input.conducted_at, notes: $input.notes, transcript: $input.transcript, existing_alternatives: $input.existing_alternatives, problem_context: $input.problem_context}
      }
    } as $data

    var $raw_change {
      value = $input.notes != null || $input.transcript != null || $input.existing_alternatives != null || $input.problem_context != null
    }

    db.transaction {
      stack {
        db.edit interviews {
          field_name = "id"
          field_value = $input.interview_id
          data = {customer_id: $access.record.customer_id}
        } as $locked

        function.run "pmf/guard/count_references" {
          input = {entity: "interview", id: $input.interview_id}
        } as $refs

        precondition (!$raw_change || $refs.total == 0) {
          error_type = "inputerror"
          error = "CITED_CONTENT_LOCKED: raw interview text is immutable once cited by evidence"
        }

        db.patch interviews {
          field_name = "id"
          field_value = $input.interview_id
          data = $data
        } as $updated
      }
    }
  }

  response = $updated
  guid = "Rh0T_BTuEe31BGWKrrK0nfPQ6xk"
}
