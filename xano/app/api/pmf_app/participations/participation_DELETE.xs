// PMF Engine: remove an eligibility mistake: open wave, no recorded response, not cited
query "participations/{participation_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an unanswered, uncited participation"
  input {
    int participation_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/participation" {
      input = {participation_id: $input.participation_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/wave" {
          input = {wave_id: $access.record.survey_wave_id}
        } as $wave

        function.run "pmf/survey/assert_wave_open" {
          input = {wave: $wave}
        } as $open

        db.get survey_participations {
          field_name = "id"
          field_value = $input.participation_id
        } as $current

        precondition ($current.responded_at == null && $current.disappointment_level == null) {
          error_type = "inputerror"
          error = "RESPONSE_RECORDED: participations with a recorded response cannot be deleted"
        }

        function.run "pmf/guard/count_references" {
          input = {entity: "participation", id: $input.participation_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the participation is cited by evidence"
        }

        db.del survey_participations {
          field_name = "id"
          field_value = $input.participation_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.participation_id}
  guid = "FYnMjUa7h3temxaRAZC-bm98m0Q"
}
