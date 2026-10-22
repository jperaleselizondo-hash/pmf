// PMF Engine: record invitation and response data; snapshot, customer and wave are immutable
// Open waves only; D-018/D-022/U14 rules; cited responses are locked (U4).
query "participations/{participation_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update invitation or response of a participation"
  input {
    int participation_id
    timestamp? invited_at?
    timestamp? responded_at?
    enum? disappointment_level? {
      values = ["very", "somewhat", "not"]
    }

    text? beneficiary_description? {
      sensitive = true
    }

    text? main_benefit? {
      sensitive = true
    }

    text? improvement_request? {
      sensitive = true
    }

    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/participation" {
      input = {participation_id: $input.participation_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values   : {invited_at: $input.invited_at, responded_at: $input.responded_at, disappointment_level: $input.disappointment_level, beneficiary_description: $input.beneficiary_description, main_benefit: $input.main_benefit, improvement_request: $input.improvement_request}
        clear    : $input.clear
        clearable: ["invited_at", "responded_at", "disappointment_level", "beneficiary_description", "main_benefit", "improvement_request"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/wave" {
          input = {wave_id: $access.record.survey_wave_id}
        } as $wave

        function.run "pmf/survey/assert_wave_open" {
          input = {wave: $wave}
        } as $open

        db.get survey_participations {
          field_name = "id"
          field_value = $input.participation_id
        } as $current

        var $merged {
          value = $current
        }

        var $response_change {
          value = false
        }

        foreach ($data|keys) {
          each as $key {
            var.update $merged {
              value = $merged|set:$key:($data|get:$key)
            }

            conditional {
              if (["responded_at", "disappointment_level", "beneficiary_description", "main_benefit", "improvement_request"]|some:$$ == $key) {
                var.update $response_change {
                  value = true
                }
              }
            }
          }
        }

        conditional {
          if ($response_change) {
            function.run "pmf/guard/count_references" {
              input = {entity: "participation", id: $input.participation_id}
            } as $refs

            precondition ($refs.total == 0) {
              error_type = "inputerror"
              error = "CITED_CONTENT_LOCKED: this response is cited by evidence and cannot be changed"
            }
          }
        }

        function.run "pmf/survey/validate_response" {
          input = {wave: $wave, state: $merged}
        } as $valid

        db.patch survey_participations {
          field_name = "id"
          field_value = $input.participation_id
          data = $data
        } as $updated
      }
    }

    function.run "pmf/survey/participation_status" {
      input = {participation: $updated}
    } as $status
  }

  response = $updated|set:"status":$status
}
