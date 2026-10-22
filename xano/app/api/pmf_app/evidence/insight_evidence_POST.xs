// PMF Engine: link an insight to exactly one original source (interview XOR survey response)
// Locks the insight and the source family so cited content cannot change concurrently.
query "insights/{insight_id}/evidence" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Add evidence to an insight"
  input {
    int insight_id
    int? interview_id?
    int? survey_participation_id?
    text? source_field? filters=trim
    text excerpt {
      sensitive = true
    }

    enum relationship {
      values = ["supports", "contradicts"]
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/insight" {
      input = {insight_id: $input.insight_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/text/normalize" {
      input = {value: $input.source_field}
    } as $source_field

    var $warnings {
      value = []
    }

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $input.insight_id}
        } as $insight

        conditional {
          if ($input.survey_participation_id != null) {
            db.get survey_participations {
              field_name = "id"
              field_value = $input.survey_participation_id
              output = ["id", "survey_wave_id"]
            } as $source_participation

            conditional {
              if ($source_participation != null) {
                function.run "pmf/lock/wave" {
                  input = {wave_id: $source_participation.survey_wave_id}
                } as $source_wave
              }
            }
          }

          elseif ($input.interview_id != null) {
            db.get interviews {
              field_name = "id"
              field_value = $input.interview_id
              output = ["id", "customer_id"]
            } as $source_interview

            conditional {
              if ($source_interview != null) {
                db.edit interviews {
                  field_name = "id"
                  field_value = $input.interview_id
                  data = {customer_id: $source_interview.customer_id}
                } as $interview_lock
              }
            }
          }
        }

        function.run "pmf/evidence/validate_source" {
          input = {insight: $insight, interview_id: $input.interview_id, survey_participation_id: $input.survey_participation_id, source_field: $source_field, excerpt: $input.excerpt}
        } as $source

        db.query insight_evidence {
          where = $db.insight_evidence.insight_id == $input.insight_id && $db.insight_evidence.excerpt == $input.excerpt
          return = {type: "list"}
          output = ["id", "interview_id", "survey_participation_id", "source_field"]
        } as $same_excerpt

        var $duplicates {
          value = $same_excerpt|filter:$$.interview_id == $input.interview_id && $$.survey_participation_id == $input.survey_participation_id && $$.source_field == $source_field
        }

        conditional {
          if (($duplicates|count) > 0) {
            var.update $warnings {
              value = $warnings|push:{code: "DUPLICATE_EVIDENCE", detail: "an identical excerpt from the same source is already linked"}
            }
          }
        }

        db.add insight_evidence {
          data = {
            insight_id             : $input.insight_id
            interview_id           : $input.interview_id
            survey_participation_id: $input.survey_participation_id
            source_field           : $source_field
            excerpt                : $input.excerpt
            relationship           : $input.relationship
          }
        } as $evidence
      }
    }
  }

  response = {evidence: $evidence, warnings: $warnings}
}
