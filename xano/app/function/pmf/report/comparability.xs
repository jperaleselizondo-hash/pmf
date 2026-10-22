// PMF Engine: cohort comparability against earlier waves of the same product (by creation order)
function "pmf/report/comparability" {
  description = "Detect definition changes and repeat respondents"
  input {
    json wave
    json rows
  }

  stack {
    db.query survey_waves {
      where = $db.survey_waves.product_id == $input.wave.product_id && $db.survey_waves.created_at < $input.wave.created_at
      sort = {created_at: "desc"}
      return = {type: "list"}
    } as $earlier

    var $previous {
      value = $earlier|first
    }

    var $changed {
      value = []
    }

    conditional {
      if ($previous != null) {
        conditional {
          if ($previous.questionnaire_version != $input.wave.questionnaire_version) {
            var.update $changed {
              value = $changed|push:"questionnaire_version"
            }
          }
        }

        conditional {
          if ($previous.eligibility_rule != $input.wave.eligibility_rule) {
            var.update $changed {
              value = $changed|push:"eligibility_rule"
            }
          }
        }
      }
    }

    var $repeat_ids {
      value = []
    }

    var $earlier_ids {
      value = $earlier|map:$$.id
    }

    var $customer_ids {
      value = ($input.rows ?? [])|map:$$.customer_id
    }

    conditional {
      if (($earlier_ids|count) > 0 && ($customer_ids|count) > 0) {
        db.query survey_participations {
          where = $db.survey_participations.survey_wave_id in $earlier_ids && $db.survey_participations.customer_id in $customer_ids && $db.survey_participations.responded_at != null && $db.survey_participations.disappointment_level != null
          return = {type: "list"}
          output = ["customer_id"]
        } as $prior

        var.update $repeat_ids {
          value = ($prior|map:$$.customer_id)|unique
        }
      }
    }

    var $previous_summary {
      value = null
    }

    conditional {
      if ($previous != null) {
        var.update $previous_summary {
          value = {id: $previous.id, name: $previous.name, questionnaire_version: $previous.questionnaire_version, eligibility_rule: $previous.eligibility_rule}
        }
      }
    }
  }

  response = {
    previous_wave       : $previous_summary
    definition_changed  : ($changed|count) > 0
    changed_fields      : $changed
    repeat_customer_ids : $repeat_ids
  }
  guid = "FpJ1_FFJ_CyUevbT5zSiBT2D8eo"
}
