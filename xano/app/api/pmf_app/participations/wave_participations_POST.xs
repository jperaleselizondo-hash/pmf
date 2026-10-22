// PMF Engine: add eligible customers to a wave (all-or-nothing); segment snapshot is server-assigned (D-005)
query "survey-waves/{wave_id}/participations" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Add eligible customers to a survey wave"
  input {
    int wave_id
    int[] customer_ids
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    var $count {
      value = $input.customer_ids|count
    }

    precondition ($count >= 1 && $count <= 200) {
      error_type = "inputerror"
      error = "INVALID_INPUT: provide between 1 and 200 customer_ids"
    }

    precondition ((($input.customer_ids|unique)|count) == $count) {
      error_type = "inputerror"
      error = "DUPLICATE_IN_REQUEST: customer_ids contains duplicates"
    }

    var $created {
      value = []
    }

    db.transaction {
      stack {
        function.run "pmf/lock/wave" {
          input = {wave_id: $input.wave_id}
        } as $wave

        function.run "pmf/survey/assert_wave_open" {
          input = {wave: $wave}
        } as $open

        db.query survey_participations {
          where = $db.survey_participations.survey_wave_id == $input.wave_id && $db.survey_participations.customer_id in $input.customer_ids
          return = {type: "list"}
          output = ["customer_id"]
        } as $existing

        precondition (($existing|count) == 0) {
          error_type = "inputerror"
          error = "DUPLICATE_PARTICIPATION: already in this wave: " ~ (($existing|map:$$.customer_id)|join:", ")
        }

        foreach ($input.customer_ids) {
          each as $customer_id {
            function.run "pmf/integrity/customer_in_product" {
              input = {customer_id: $customer_id, product_id: $wave.product_id}
            } as $customer

            db.add survey_participations {
              data = {
                survey_wave_id     : $input.wave_id
                customer_id        : $customer_id
                segment_id_snapshot: $customer.segment_id
              }
            } as $participation

            var.update $created {
              value = $created|push:$participation
            }
          }
        }
      }
    }
  }

  response = {created: $created}
  guid = "3ZGTcM2nY9HC0c2CcxKMqnKo8rs"
}
