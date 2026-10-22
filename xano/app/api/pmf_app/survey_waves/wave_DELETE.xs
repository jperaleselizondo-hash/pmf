// PMF Engine: delete a survey wave only when it has no participants
query "survey-waves/{wave_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an empty survey wave"
  input {
    int wave_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/wave" {
          input = {wave_id: $input.wave_id}
        } as $wave

        function.run "pmf/guard/count_references" {
          input = {entity: "wave", id: $input.wave_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the survey wave has participants"
        }

        db.del survey_waves {
          field_name = "id"
          field_value = $input.wave_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.wave_id}
  guid = "oZYcm0_KngCcyO5UUW1dZ8MZPFQ"
}
