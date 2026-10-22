// PMF Engine: customer detail with interview dates and survey participation history
query "customers/{customer_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get a customer with related interviews and participations"
  input {
    int customer_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/customer" {
      input = {customer_id: $input.customer_id, auth_id: $auth.id}
    } as $access

    var $customer {
      value = $access.record
    }

    var $segment {
      value = null
    }

    conditional {
      if ($customer.segment_id != null) {
        db.get segments {
          field_name = "id"
          field_value = $customer.segment_id
          output = ["id", "name"]
        } as $current_segment

        var.update $segment {
          value = $current_segment
        }
      }
    }

    db.query interviews {
      where = $db.interviews.customer_id == $customer.id
      sort = {conducted_at: "desc"}
      return = {type: "list"}
      output = ["id", "conducted_at"]
    } as $interviews

    db.query survey_participations {
      join = {
        survey_waves: {table: "survey_waves", type: "inner", where: $db.survey_participations.survey_wave_id == $db.survey_waves.id}
      }

      where = $db.survey_participations.customer_id == $customer.id
      sort = {created_at: "desc"}
      eval = {wave_name: $db.survey_waves.name}
      return = {type: "list"}
      output = ["id", "survey_wave_id", "segment_id_snapshot", "invited_at", "responded_at", "disappointment_level", "wave_name"]
    } as $rows

    var $participations {
      value = []
    }

    foreach ($rows) {
      each as $row {
        function.run "pmf/survey/participation_status" {
          input = {participation: $row}
        } as $status

        var.update $participations {
          value = $participations|push:{id: $row.id, wave: {id: $row.survey_wave_id, name: $row.wave_name}, segment_id_snapshot: $row.segment_id_snapshot, invited_at: $row.invited_at, responded_at: $row.responded_at, disappointment_level: $row.disappointment_level, status: $status}
        }
      }
    }

    var $out {
      value = $customer|set:"segment":($segment)
    }

    var.update $out {
      value = $out|set:"interviews":($interviews)
    }

    var.update $out {
      value = $out|set:"participations":($participations)
    }
  }

  response = $out
}
