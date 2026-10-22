// PMF Engine: experiment date, conclusion and decision consistency (proposal §4.6)
function "pmf/validation/validate_experiment" {
  description = "Validate an experiment's merged state"
  input {
    json experiment
  }

  stack {
    var $e {
      value = $input.experiment
    }

    precondition ($e.ended_at == null || $e.started_at != null) {
      error_type = "inputerror"
      error = "EXPERIMENT_DATES: ended_at requires started_at"
    }

    precondition ($e.ended_at == null || $e.ended_at >= $e.started_at) {
      error_type = "inputerror"
      error = "EXPERIMENT_DATES: ended_at must not be before started_at"
    }

    function.run "pmf/text/is_blank" {
      input = {value: $e.observed_result}
    } as $observed_blank

    precondition ($e.conclusion == null || !$observed_blank) {
      error_type = "inputerror"
      error = "EXPERIMENT_CONCLUSION: a conclusion requires a recorded observed_result"
    }

    precondition ($e.decision == null || $e.conclusion != null) {
      error_type = "inputerror"
      error = "EXPERIMENT_DECISION: a decision requires a conclusion"
    }
  }

  response = true

  test "ended before started is rejected" {
    input = {experiment: {started_at: 2000, ended_at: 1000}}
    expect.to_throw
  }

  test "ended without start is rejected" {
    input = {experiment: {started_at: null, ended_at: 1000}}
    expect.to_throw
  }

  test "decision without conclusion is rejected" {
    input = {experiment: {decision: "adopt", conclusion: null}}
    expect.to_throw
  }

  test "conclusion without observed result is rejected" {
    input = {experiment: {conclusion: "supported", observed_result: " "}}
    expect.to_throw
  }

  test "complete experiment passes" {
    input = {experiment: {started_at: 1000, ended_at: 2000, observed_result: "12 of 20 activated", conclusion: "supported", decision: "adopt"}}
    expect.to_be_true ($response)
  }
  guid = "KA3XdhzcfGF3B_0OrUCbgh-jSw8"
}
