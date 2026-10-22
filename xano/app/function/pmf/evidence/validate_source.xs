// PMF Engine: evidence must cite exactly one original source in the insight's product (D-028, R8.1)
// Survey sources: responded participation, source_field required, cited answer non-blank.
// Interview sources: source_field optional; cited field (or at least one raw field) non-blank.
function "pmf/evidence/validate_source" {
  description = "Validate an evidence source, cited field and excerpt"
  input {
    json insight
    int? interview_id?
    int? survey_participation_id?
    text? source_field?
    text? excerpt? {
      sensitive = true
    }
  }

  stack {
    var $has_interview {
      value = $input.interview_id != null
    }

    var $has_participation {
      value = $input.survey_participation_id != null
    }

    precondition ($has_interview != $has_participation) {
      error_type = "inputerror"
      error = "EVIDENCE_SOURCE_XOR: provide exactly one of interview_id or survey_participation_id"
    }

    function.run "pmf/text/is_blank" {
      input = {value: $input.excerpt}
    } as $excerpt_blank

    precondition (!$excerpt_blank) {
      error_type = "inputerror"
      error = "EXCERPT_REQUIRED: the excerpt must contain the verifiable observation"
    }

    var $kind {
      value = null
    }

    var $source_product_id {
      value = null
    }

    conditional {
      if ($has_interview) {
        db.get interviews {
          field_name = "id"
          field_value = $input.interview_id
        } as $interview

        precondition ($interview != null) {
          error_type = "inputerror"
          error = "SOURCE_NOT_FOUND: interview not found"
        }

        db.get customers {
          field_name = "id"
          field_value = $interview.customer_id
        } as $interview_customer

        var.update $source_product_id {
          value = $interview_customer.product_id
        }

        var.update $kind {
          value = "interview"
        }

        conditional {
          if ($input.source_field == null) {
            function.run "pmf/text/is_blank" {
              input = {value: ($interview.notes ?? "") ~ ($interview.transcript ?? "") ~ ($interview.existing_alternatives ?? "") ~ ($interview.problem_context ?? "")}
            } as $interview_blank

            precondition (!$interview_blank) {
              error_type = "inputerror"
              error = "SOURCE_EMPTY: the interview has no recorded content to cite"
            }
          }

          else {
            precondition (["notes", "transcript", "existing_alternatives", "problem_context"]|some:$$ == $input.source_field) {
              error_type = "inputerror"
              error = "INVALID_SOURCE_FIELD: interview evidence may cite notes, transcript, existing_alternatives or problem_context"
            }

            function.run "pmf/text/is_blank" {
              input = {value: $interview|get:$input.source_field}
            } as $field_blank

            precondition (!$field_blank) {
              error_type = "inputerror"
              error = "SOURCE_FIELD_EMPTY: the cited interview field is blank"
            }
          }
        }
      }

      else {
        db.get survey_participations {
          field_name = "id"
          field_value = $input.survey_participation_id
        } as $participation

        precondition ($participation != null) {
          error_type = "inputerror"
          error = "SOURCE_NOT_FOUND: survey participation not found"
        }

        db.get survey_waves {
          field_name = "id"
          field_value = $participation.survey_wave_id
        } as $participation_wave

        var.update $source_product_id {
          value = $participation_wave.product_id
        }

        var.update $kind {
          value = "survey"
        }

        precondition ($participation.responded_at != null) {
          error_type = "inputerror"
          error = "SURVEY_SOURCE_NOT_RESPONDED: only recorded survey responses can be cited"
        }

        precondition ($input.source_field != null && (["beneficiary_description", "main_benefit", "improvement_request"]|some:$$ == $input.source_field)) {
          error_type = "inputerror"
          error = "INVALID_SOURCE_FIELD: survey evidence must cite beneficiary_description, main_benefit or improvement_request"
        }

        function.run "pmf/text/is_blank" {
          input = {value: $participation|get:$input.source_field}
        } as $answer_blank

        precondition (!$answer_blank) {
          error_type = "inputerror"
          error = "SOURCE_FIELD_EMPTY: the cited survey answer is blank"
        }
      }
    }

    precondition ($source_product_id == $input.insight.product_id) {
      error_type = "inputerror"
      error = "CROSS_PRODUCT_REFERENCE: the evidence source belongs to a different product"
    }
  }

  response = {kind: $kind, product_id: $source_product_id}
}
