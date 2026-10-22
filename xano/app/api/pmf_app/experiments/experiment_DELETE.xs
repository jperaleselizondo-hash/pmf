// PMF Engine: delete an unconcluded experiment; tested hypotheses must keep at least one experiment (U8)
query "experiments/{experiment_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an unconcluded experiment"
  input {
    int experiment_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/experiment" {
      input = {experiment_id: $input.experiment_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.insight.id}
        } as $insight

        db.get experiments {
          field_name = "id"
          field_value = $input.experiment_id
        } as $current

        precondition ($current.conclusion == null && $current.decision == null) {
          error_type = "inputerror"
          error = "EXPERIMENT_CONCLUDED: experiments with a recorded conclusion or decision are preserved"
        }

        db.get hypotheses {
          field_name = "id"
          field_value = $current.hypothesis_id
        } as $hypothesis

        conditional {
          if ($hypothesis.status != "proposed") {
            db.query experiments {
              where = $db.experiments.hypothesis_id == $current.hypothesis_id
              return = {type: "count"}
            } as $experiment_count

            precondition ($experiment_count > 1) {
              error_type = "inputerror"
              error = "HYPOTHESIS_NEEDS_EXPERIMENT: a hypothesis beyond proposed must keep at least one experiment"
            }
          }
        }

        db.del experiments {
          field_name = "id"
          field_value = $input.experiment_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.experiment_id}
  guid = "kFIZQ1KOF4Ip6FtXT_z6fm4ik7U"
}
