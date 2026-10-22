// PMF Engine: update a survey wave (open waves only; definition frozen once participants exist)
query "survey-waves/{wave_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update a survey wave"
  input {
    int wave_id
    text? name? filters=trim
    text? eligibility_rule? filters=trim
    text? questionnaire_version? filters=trim
    timestamp? started_at?
    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values   : {name: $input.name, eligibility_rule: $input.eligibility_rule, questionnaire_version: $input.questionnaire_version, started_at: $input.started_at}
        clear    : $input.clear
        clearable: ["started_at"]
        required : ["name", "eligibility_rule", "questionnaire_version"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/wave" {
          input = {wave_id: $input.wave_id}
        } as $wave

        function.run "pmf/survey/assert_wave_open" {
          input = {wave: $wave}
        } as $open

        conditional {
          if (($input.eligibility_rule != null && $input.eligibility_rule != $wave.eligibility_rule) || ($input.questionnaire_version != null && $input.questionnaire_version != $wave.questionnaire_version)) {
            function.run "pmf/survey/assert_definition_unlocked" {
              input = {wave_id: $input.wave_id}
            } as $unlocked
          }
        }

        var $start_change {
          value = $input.started_at != null || (($input.clear ?? [])|some:$$ == "started_at")
        }

        conditional {
          if ($start_change) {
            db.query survey_participations {
              where = $db.survey_participations.survey_wave_id == $input.wave_id && $db.survey_participations.responded_at != null
              sort = {responded_at: "asc"}
              return = {type: "single"}
              output = ["id", "responded_at"]
            } as $earliest

            precondition ($earliest == null || ($input.started_at != null && $input.started_at <= $earliest.responded_at)) {
              error_type = "inputerror"
              error = "INVALID_TIMESTAMP: started_at cannot move after the earliest recorded response"
            }
          }
        }

        db.patch survey_waves {
          field_name = "id"
          field_value = $input.wave_id
          data = $data
        } as $updated
      }
    }
  }

  response = $updated
}
