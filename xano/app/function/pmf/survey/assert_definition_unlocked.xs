// PMF Engine: eligibility rule and questionnaire version are fixed once a wave has participants (D-005)
function "pmf/survey/assert_definition_unlocked" {
  description = "Reject definition changes after participants exist"
  input {
    int wave_id
  }

  stack {
    db.query survey_participations {
      where = $db.survey_participations.survey_wave_id == $input.wave_id
      return = {type: "count"}
    } as $participants

    precondition ($participants == 0) {
      error_type = "inputerror"
      error = "DEFINITION_LOCKED: eligibility rule and questionnaire version are fixed once participants exist"
    }
  }

  response = true
}
