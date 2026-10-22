// PMF Engine: full PMF report for a wave (overall, selected scope, by snapshot segment, first-time only, warnings)
// Segment scoping always uses segment_id_snapshot, never the customer's current segment.
function "pmf/report/build_wave_report" {
  description = "Assemble the PMF wave report contract"
  input {
    json wave
    int? segment_id?
    bool unsegmented?=false
    bool summary?=false
  }

  stack {
    db.query survey_participations {
      where = $db.survey_participations.survey_wave_id == $input.wave.id
      return = {type: "list"}
      output = ["id", "customer_id", "segment_id_snapshot", "invited_at", "responded_at", "disappointment_level"]
    } as $rows

    function.run "pmf/report/count_wave" {
      input = {rows: $rows}
    } as $overall_counts

    function.run "pmf/report/compute_pmf" {
      input = {counts: $overall_counts}
    } as $overall

    function.run "pmf/survey/wave_state" {
      input = {wave: $input.wave}
    } as $state

    function.run "pmf/report/comparability" {
      input = {wave: $input.wave, rows: $rows}
    } as $cmp

    var $warnings {
      value = []
    }

    conditional {
      if ($state != "closed") {
        var.update $warnings {
          value = $warnings|push:{code: "WAVE_OPEN", detail: "results are provisional until the wave is closed"}
        }
      }
    }

    conditional {
      if ($cmp.definition_changed) {
        var.update $warnings {
          value = $warnings|push:{code: "DEFINITION_CHANGED", detail: "differs from previous wave in: " ~ ($cmp.changed_fields|join:", ")}
        }
      }
    }

    conditional {
      if (($cmp.repeat_customer_ids|count) > 0) {
        var.update $warnings {
          value = $warnings|push:{code: "REPEAT_RESPONDENTS", detail: ($cmp.repeat_customer_ids|count) ~ " participant(s) gave a valid response in an earlier wave"}
        }
      }
    }

    conditional {
      if ($overall_counts.unsegmented_count > 0) {
        var.update $warnings {
          value = $warnings|push:{code: "UNSEGMENTED_PARTICIPANTS", detail: $overall_counts.unsegmented_count ~ " participant(s) had no segment at eligibility"}
        }
      }
    }

    conditional {
      if ($overall_counts.anomaly_count > 0) {
        var.update $warnings {
          value = $warnings|push:{code: "DATA_ANOMALY", detail: $overall_counts.anomaly_count ~ " row(s) have a category without responded_at; never scored"}
        }
      }
    }

    var $wave_summary {
      value = {id: $input.wave.id, name: $input.wave.name, product_id: $input.wave.product_id, state: $state, started_at: $input.wave.started_at, closed_at: $input.wave.closed_at, questionnaire_version: $input.wave.questionnaire_version, eligibility_rule: $input.wave.eligibility_rule}
    }

    conditional {
      if ($input.summary) {
        conditional {
          if ($overall.valid_response_count == 0) {
            var.update $warnings {
              value = $warnings|push:{code: "NO_VALID_RESPONSES", detail: "PMF is undefined without valid responses"}
            }
          }

          elseif ($overall.small_sample) {
            var.update $warnings {
              value = $warnings|push:{code: "SMALL_SAMPLE", detail: $overall.valid_response_count ~ " valid responses (fewer than 30); informational only"}
            }
          }
        }

        return {
          value = {wave: $wave_summary, overall: $overall, comparable_with_previous: !$cmp.definition_changed, warnings: $warnings}
        }
      }
    }

    db.query segments {
      where = $db.segments.product_id == $input.wave.product_id
      sort = {name: "asc"}
      return = {type: "list"}
      output = ["id", "name"]
    } as $segments

    var $selected_rows {
      value = $rows
    }

    var $selected_segment {
      value = null
    }

    conditional {
      if ($input.segment_id != null) {
        var.update $selected_rows {
          value = $rows|filter:$$.segment_id_snapshot == $input.segment_id
        }

        var.update $selected_segment {
          value = $segments|find:$$.id == $input.segment_id
        }
      }

      elseif ($input.unsegmented) {
        var.update $selected_rows {
          value = $rows|filter:$$.segment_id_snapshot == null
        }
      }
    }

    function.run "pmf/report/count_wave" {
      input = {rows: $selected_rows}
    } as $selected_counts

    function.run "pmf/report/compute_pmf" {
      input = {counts: $selected_counts}
    } as $selected

    conditional {
      if ($selected.valid_response_count == 0) {
        var.update $warnings {
          value = $warnings|push:{code: "NO_VALID_RESPONSES", detail: "PMF is undefined without valid responses in the selected scope"}
        }
      }

      elseif ($selected.small_sample) {
        var.update $warnings {
          value = $warnings|push:{code: "SMALL_SAMPLE", detail: $selected.valid_response_count ~ " valid responses (fewer than 30); informational only, not a statistical claim"}
        }
      }
    }

    var $by_segment {
      value = []
    }

    foreach ($segments) {
      each as $segment {
        var $segment_rows {
          value = $rows|filter:$$.segment_id_snapshot == $segment.id
        }

        function.run "pmf/report/count_wave" {
          input = {rows: $segment_rows}
        } as $segment_counts

        function.run "pmf/report/compute_pmf" {
          input = {counts: $segment_counts}
        } as $segment_result

        var.update $by_segment {
          value = $by_segment|push:{segment: $segment, label: $segment.name, result: $segment_result}
        }
      }
    }

    var $unsegmented_rows {
      value = $rows|filter:$$.segment_id_snapshot == null
    }

    function.run "pmf/report/count_wave" {
      input = {rows: $unsegmented_rows}
    } as $unsegmented_counts

    function.run "pmf/report/compute_pmf" {
      input = {counts: $unsegmented_counts}
    } as $unsegmented_result

    var.update $by_segment {
      value = $by_segment|push:{segment: null, label: "unsegmented", result: $unsegmented_result}
    }

    var $first_time_rows {
      value = []
    }

    foreach ($selected_rows) {
      each as $row {
        conditional {
          if (!($cmp.repeat_customer_ids|some:$$ == $row.customer_id)) {
            var.update $first_time_rows {
              value = $first_time_rows|push:$row
            }
          }
        }
      }
    }

    function.run "pmf/report/count_wave" {
      input = {rows: $first_time_rows}
    } as $first_time_counts

    function.run "pmf/report/compute_pmf" {
      input = {counts: $first_time_counts}
    } as $first_time_result
  }

  response = {
    wave                    : $wave_summary
    filter                  : {segment_id: $input.segment_id, unsegmented: $input.unsegmented, segment: $selected_segment}
    selected                : $selected
    overall                 : $overall
    by_segment              : $by_segment
    first_time_only         : {excluded_repeat_respondents: ($selected_rows|count) - ($first_time_rows|count), result: $first_time_result}
    comparable_with_previous: !$cmp.definition_changed
    previous_wave           : $cmp.previous_wave
    warnings                : $warnings
    generated_at            : now
  }
}
