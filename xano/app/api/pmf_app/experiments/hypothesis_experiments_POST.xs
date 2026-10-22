// PMF Engine: record an experiment for a hypothesis (founder text trimmed, D-027); never changes hypothesis status
query "hypotheses/{hypothesis_id}/experiments" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create an experiment"
  input {
    int hypothesis_id
    text name filters=trim
    text method filters=trim
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
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/hypothesis" {
      input = {hypothesis_id: $input.hypothesis_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values  : {name: $input.name, method: $input.method, started_at: $input.started_at, ended_at: $input.ended_at, baseline: $input.baseline, target: $input.target, observed_result: $input.observed_result, conclusion: $input.conclusion, decision: $input.decision, notes: $input.notes}
        required: ["name", "method"]
        touch   : false
      }
    } as $data

    var $state {
      value = {started_at: $data|get:"started_at", ended_at: $data|get:"ended_at", observed_result: $data|get:"observed_result", conclusion: $data|get:"conclusion", decision: $data|get:"decision"}
    }

    function.run "pmf/validation/validate_experiment" {
      input = {experiment: $state}
    } as $valid

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.record.insight_id}
        } as $insight

        db.add experiments {
          data = {
            hypothesis_id  : $input.hypothesis_id
            name           : $data.name
            method         : $data.method
            started_at     : $data|get:"started_at"
            ended_at       : $data|get:"ended_at"
            baseline       : $data|get:"baseline"
            target         : $data|get:"target"
            observed_result: $data|get:"observed_result"
            conclusion     : $data|get:"conclusion"
            decision       : $data|get:"decision"
            notes          : $data|get:"notes"
          }
        } as $experiment
      }
    }
  }

  response = $experiment
  guid = "YfrmflQ5YpAAOrjgi-Mrfquy3BE"
}
