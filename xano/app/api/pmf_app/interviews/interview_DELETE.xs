// PMF Engine: delete an interview only when no evidence cites it
query "interviews/{interview_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an uncited interview"
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

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the interview is cited by evidence"
        }

        db.del interviews {
          field_name = "id"
          field_value = $input.interview_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.interview_id}
}
