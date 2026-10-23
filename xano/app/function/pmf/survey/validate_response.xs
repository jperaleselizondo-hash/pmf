// PMF Engine: response state and timestamp rules (D-018, D-022, U14)
// `state` is the participation after the requested change is applied.
function "pmf/survey/validate_response" {
  description = "Validate a participation's invitation and response state"
  input {
    json wave
    json state
  }

  stack {
    // Optional fields are read with `|get:` (verified to return null for a missing key), so partial states
    // behave exactly like database rows whose optional columns are null.
    var $invited_at {
      value = $input.state|get:"invited_at"
    }

    var $responded_at {
      value = $input.state|get:"responded_at"
    }

    var $level {
      value = $input.state|get:"disappointment_level"
    }

    var $beneficiary {
      value = $input.state|get:"beneficiary_description"
    }

    var $benefit {
      value = $input.state|get:"main_benefit"
    }

    var $improvement {
      value = $input.state|get:"improvement_request"
    }

    var $started_at {
      value = $input.wave|get:"started_at"
    }

    var $limit {
      value = now|transform_timestamp:"+5 minutes"
    }

    var $has_answers {
      value = $level != null || $beneficiary != null || $benefit != null || $improvement != null
    }

    precondition (!$has_answers || $responded_at != null) {
      error_type = "inputerror"
      error = "RESPONSE_STATE: a disappointment category or answer requires responded_at"
    }

    precondition ($invited_at == null || $invited_at <= $limit) {
      error_type = "inputerror"
      error = "INVALID_TIMESTAMP: invited_at is in the future"
    }

    conditional {
      if ($responded_at != null) {
        precondition ($started_at != null) {
          error_type = "inputerror"
          error = "WAVE_NOT_STARTED: set the wave start before recording responses"
        }

        precondition ($responded_at >= $started_at) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: responded_at is before the wave started"
        }

        precondition ($responded_at <= $limit) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: responded_at is in the future"
        }

        precondition ($invited_at == null || $invited_at <= $responded_at) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: invited_at is after responded_at"
        }
      }
    }
  }

  response = true

  test "responded_at without category is allowed (incomplete)" {
    input = {wave: {started_at: 1000}, state: {responded_at: 2000, disappointment_level: null}}
    expect.to_be_true ($response)
  }

  test "partial state: responded_at only is allowed (incomplete)" {
    input = {wave: {started_at: 1000}, state: {responded_at: 2000}}
    expect.to_be_true ($response)
  }

  test "partial state: invitation only is allowed" {
    input = {wave: {started_at: 1000}, state: {invited_at: 1500}}
    expect.to_be_true ($response)
  }

  test "partial state: empty state is allowed (eligible)" {
    input = {wave: {}, state: {}}
    expect.to_be_true ($response)
  }

  test "partial state: response with answers and no invitation passes" {
    input = {wave: {started_at: 1000}, state: {responded_at: 2000, disappointment_level: "very", main_benefit: "speed"}}
    expect.to_be_true ($response)
  }

  test "complete row: valid historical response passes" {
    input = {
      wave : {started_at: 1000, closed_at: null}
      state: {invited_at: 1500, responded_at: 2000, disappointment_level: "very", beneficiary_description: null, main_benefit: "speed", improvement_request: null}
    }

    expect.to_be_true ($response)
  }

  test "complete row: category without responded_at is rejected" {
    input = {
      wave : {started_at: 1000}
      state: {invited_at: null, responded_at: null, disappointment_level: "very", beneficiary_description: null, main_benefit: null, improvement_request: null}
    }

    expect.to_throw
  }

  test "complete row: answer text without responded_at is rejected" {
    input = {
      wave : {started_at: 1000}
      state: {invited_at: null, responded_at: null, disappointment_level: null, beneficiary_description: null, main_benefit: "speed", improvement_request: null}
    }

    expect.to_throw
  }

  test "complete row: response before wave start is rejected" {
    input = {
      wave : {started_at: 5000}
      state: {invited_at: null, responded_at: 2000, disappointment_level: "not", beneficiary_description: null, main_benefit: null, improvement_request: null}
    }

    expect.to_throw
  }

  test "complete row: response on unstarted wave is rejected" {
    input = {
      wave : {started_at: null}
      state: {invited_at: null, responded_at: 2000, disappointment_level: "not", beneficiary_description: null, main_benefit: null, improvement_request: null}
    }

    expect.to_throw
  }

  test "complete row: invitation after response is rejected" {
    input = {
      wave : {started_at: 1000}
      state: {invited_at: 3000, responded_at: 2000, disappointment_level: "somewhat", beneficiary_description: null, main_benefit: null, improvement_request: null}
    }

    expect.to_throw
  }

  test "complete row: future response is rejected" {
    input = {
      wave : {started_at: 1000}
      state: {invited_at: null, responded_at: 9999999999999, disappointment_level: "not", beneficiary_description: null, main_benefit: null, improvement_request: null}
    }

    expect.to_throw
  }
  guid = "Pa3AIbNrZ8QT8odb2VJUxgypZw0"
}
