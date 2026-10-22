// PMF Engine: update an experiment; a validated hypothesis must keep at least one supported experiment
query "experiments/{experiment_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update an experiment"
  input {
    int experiment_id
    text? name? filters=trim
    text? method? filters=trim
    timestamp? started_at?
    timestamp? ended_at?
    text? baseline? filters=trim
    text? target? filters=trim
    text? observed_result? filters=trim {
      sensitive = true
    }

    enum? conclusion? {
      values = ["supported", "refuted", "inconclusive"]
    }

    enum? decision? {
      values = ["adopt", "iterate", "reject", "investigate"]
    }

    text? notes? filters=trim {
      sensitive = true
    }

    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/experiment" {
      input = {experiment_id: $input.experiment_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values   : {name: $input.name, method: $input.method, started_at: $input.started_at, ended_at: $input.ended_at, baseline: $input.baseline, target: $input.target, observed_result: $input.observed_result, conclusion: $input.conclusion, decision: $input.decision, notes: $input.notes}
        clear    : $input.clear
        clearable: ["started_at", "ended_at", "baseline", "target", "observed_result", "conclusion", "decision", "notes"]
        required : ["name", "method"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.insight.id}
        } as $insight

        db.get experiments {
          field_name = "id"
          field_value = $input.experiment_id
        } as $current

        var $merged {
          value = $current
        }

        foreach ($data|keys) {
          each as $key {
            var.update $merged {
              value = $merged|set:$key:($data|get:$key)
            }
          }
        }

        function.run "pmf/validation/validate_experiment" {
          input = {experiment: $merged}
        } as $valid

        db.get hypotheses {
          field_name = "id"
          field_value = $current.hypothesis_id
        } as $hypothesis

        conditional {
          if ($hypothesis.status == "validated" && $merged.conclusion != "supported") {
            db.query experiments {
              where = $db.experiments.hypothesis_id == $current.hypothesis_id && $db.experiments.id != $input.experiment_id && $db.experiments.conclusion == "supported"
              return = {type: "count"}
            } as $other_supported

            precondition ($other_supported > 0) {
              error_type = "inputerror"
              error = "HYPOTHESIS_STATUS_DEPENDS: a validated hypothesis must keep at least one supported experiment"
            }
          }
        }

        db.patch experiments {
          field_name = "id"
          field_value = $input.experiment_id
          data = $data
        } as $updated
      }
    }
  }

  response = $updated
}
