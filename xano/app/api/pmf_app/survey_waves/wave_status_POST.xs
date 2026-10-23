// PMF Engine: explicit close/reopen of a survey wave (D-021); closed_at records when the wave was locked
query "survey-waves/{wave_id}/status" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Close or reopen a survey wave"
  input {
    int wave_id
    enum action {
      values = ["close", "reopen"]
    }

    timestamp? closed_at?
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

        conditional {
          if ($input.action == "close") {
            precondition ($wave.closed_at == null) {
              error_type = "inputerror"
              error = "WAVE_ALREADY_CLOSED: the survey wave is already closed"
            }

            // Runtime fix (2026-10-23): `$input.closed_at ?? now` followed by `<= now` rejected every close without
            // closed_at. The server time is read once (documented `var … = now` form) and only a client-supplied
            // closed_at is compared with it; no tolerance is added.
            var $now {
              value = now
            }

            var $closed_at {
              value = $now
            }

            conditional {
              if ($input.closed_at != null) {
                precondition ($input.closed_at <= $now) {
                  error_type = "inputerror"
                  error = "INVALID_TIMESTAMP: closed_at must not be in the future"
                }

                var.update $closed_at {
                  value = $input.closed_at
                }
              }
            }

            db.query survey_participations {
              where = $db.survey_participations.survey_wave_id == $input.wave_id && $db.survey_participations.responded_at != null
              sort = {responded_at: "desc"}
              return = {type: "single"}
              output = ["id", "responded_at"]
            } as $latest

            precondition ($latest == null || $closed_at >= $latest.responded_at) {
              error_type = "inputerror"
              error = "INVALID_TIMESTAMP: closed_at must not precede the latest recorded response"
            }

            db.edit survey_waves {
              field_name = "id"
              field_value = $input.wave_id
              data = {closed_at: $closed_at, updated_at: now}
            } as $updated
          }

          else {
            precondition ($wave.closed_at != null) {
              error_type = "inputerror"
              error = "WAVE_NOT_CLOSED: only a closed survey wave can be reopened"
            }

            precondition ($input.closed_at == null) {
              error_type = "inputerror"
              error = "INVALID_INPUT: closed_at is only accepted when closing"
            }

            db.edit survey_waves {
              field_name = "id"
              field_value = $input.wave_id
              data = {closed_at: null, updated_at: now}
            } as $updated
          }
        }
      }
    }

    function.run "pmf/survey/wave_state" {
      input = {wave: $updated}
    } as $state
  }

  response = $updated|set:"state":$state
  guid = "dI5rPk_WfHfZ4kcx1FYSaM7Mkxo"
}
