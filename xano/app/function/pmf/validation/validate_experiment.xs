// PMF Engine: experiment date, conclusion and decision consistency (proposal §4.6)
function "pmf/validation/validate_experiment" {
  description = "Validate an experiment's merged state"
  input {
    json experiment
  }

  stack {
    // Optional fields are read with `|get:` (null for a missing key): callers may pass partial states, and the
    // server may store the caller's state object in expression mode.
    var $started_at {
      value = $input.experiment|get:"started_at"
    }

    var $ended_at {
      value = $input.experiment|get:"ended_at"
    }

    var $observed_result {
      value = $input.experiment|get:"observed_result"
    }

    var $conclusion {
      value = $input.experiment|get:"conclusion"
    }

    var $decision {
      value = $input.experiment|get:"decision"
    }

    precondition ($ended_at == null || $started_at != null) {
      error_type = "inputerror"
      error = "EXPERIMENT_DATES: ended_at requires started_at"
    }

    precondition ($ended_at == null || $ended_at >= $started_at) {
      error_type = "inputerror"
      error = "EXPERIMENT_DATES: ended_at must not be before started_at"
    }

    function.run "pmf/text/is_blank" {
      input = {value: $observed_result}
    } as $observed_blank

    precondition ($conclusion == null || !$observed_blank) {
      error_type = "inputerror"
      error = "EXPERIMENT_CONCLUSION: a conclusion requires a recorded observed_result"
    }

    precondition ($decision == null || $conclusion != null) {
      error_type = "inputerror"
      error = "EXPERIMENT_DECISION: a decision requires a conclusion"
    }
  }

  response = true

  test "ended before started is rejected" {
    input = {experiment: {started_at: 2000, ended_at: 1000}}
    expect.to_throw {
      exception = "EXPERIMENT_DATES: ended_at must not be before started_at"
    }
  }

  test "ended without start is rejected" {
    input = {experiment: {started_at: null, ended_at: 1000}}
    expect.to_throw {
      exception = "EXPERIMENT_DATES: ended_at requires started_at"
    }
  }

  test "decision without conclusion is rejected" {
    input = {experiment: {decision: "adopt", conclusion: null}}
    expect.to_throw {
      exception = "EXPERIMENT_DECISION: a decision requires a conclusion"
    }
  }

  test "conclusion without observed result is rejected" {
    input = {experiment: {conclusion: "supported", observed_result: " "}}
    expect.to_throw {
      exception = "EXPERIMENT_CONCLUSION: a conclusion requires a recorded observed_result"
    }
  }

  test "partial state: name-only experiment passes" {
    input = {experiment: {}}
    expect.to_be_true ($response)
  }

  test "partial state: start only passes" {
    input = {experiment: {started_at: 1000}}
    expect.to_be_true ($response)
  }

  test "complete state with nulls passes" {
    input = {experiment: {started_at: null, ended_at: null, observed_result: null, conclusion: null, decision: null}}
    expect.to_be_true ($response)
  }

  test "complete state: ended before started is rejected" {
    input = {experiment: {started_at: 2000, ended_at: 1000, observed_result: null, conclusion: null, decision: null}}
    expect.to_throw {
      exception = "EXPERIMENT_DATES: ended_at must not be before started_at"
    }
  }

  test "complete state: decision without conclusion is rejected" {
    input = {experiment: {started_at: 1000, ended_at: 2000, observed_result: "12 of 20", conclusion: null, decision: "adopt"}}
    expect.to_throw {
      exception = "EXPERIMENT_DECISION: a decision requires a conclusion"
    }
  }

  test "complete experiment passes" {
    input = {experiment: {started_at: 1000, ended_at: 2000, observed_result: "12 of 20 activated", conclusion: "supported", decision: "adopt"}}
    expect.to_be_true ($response)
  }
  guid = "KA3XdhzcfGF3B_0OrUCbgh-jSw8"
}
