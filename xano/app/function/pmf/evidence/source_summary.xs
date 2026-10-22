// PMF Engine: display data for an evidence source (customer, date, wave)
function "pmf/evidence/source_summary" {
  description = "Summarize the original source of an evidence link"
  input {
    json evidence
  }

  stack {
    var $summary {
      value = null
    }

    conditional {
      if ($input.evidence.interview_id != null) {
        db.get interviews {
          field_name = "id"
          field_value = $input.evidence.interview_id
          output = ["id", "customer_id", "conducted_at"]
        } as $interview

        db.get customers {
          field_name = "id"
          field_value = $interview.customer_id
          output = ["id", "name", "external_id"]
        } as $customer

        var.update $summary {
          value = {kind: "interview", id: $interview.id, date: $interview.conducted_at, customer: $customer, wave: null}
        }
      }

      elseif ($input.evidence.survey_participation_id != null) {
        db.get survey_participations {
          field_name = "id"
          field_value = $input.evidence.survey_participation_id
          output = ["id", "customer_id", "survey_wave_id", "responded_at"]
        } as $participation

        db.get customers {
          field_name = "id"
          field_value = $participation.customer_id
          output = ["id", "name", "external_id"]
        } as $customer

        db.get survey_waves {
          field_name = "id"
          field_value = $participation.survey_wave_id
          output = ["id", "name"]
        } as $wave

        var.update $summary {
          value = {kind: "survey", id: $participation.id, date: $participation.responded_at, customer: $customer, wave: $wave}
        }
      }
    }
  }

  response = $summary
  guid = "0rigHlPz9fsiH6BvatWhTIAMAMc"
}
