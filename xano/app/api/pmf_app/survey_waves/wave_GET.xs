// PMF Engine: survey wave detail with state, funnel and definition lock
query "survey-waves/{wave_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get a survey wave"
  input {
    int wave_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/survey/wave_state" {
      input = {wave: $access.record}
    } as $state

    db.query survey_participations {
      where = $db.survey_participations.survey_wave_id == $input.wave_id
      return = {type: "list"}
      output = ["id", "customer_id", "segment_id_snapshot", "invited_at", "responded_at", "disappointment_level"]
    } as $rows

    function.run "pmf/report/count_wave" {
      input = {rows: $rows}
    } as $funnel

    var $locked {
      value = $funnel.eligible_count > 0
    }

    var $out {
      value = $access.record|set:"state":($state)
    }

    var.update $out {
      value = $out|set:"funnel":($funnel)
    }

    var.update $out {
      value = $out|set:"definition_locked":($locked)
    }
  }

  response = $out
  guid = "pMmHOaaNSMu9R3cE7tgQ2VDwISU"
}
