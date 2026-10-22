// PMF Engine: response state and timestamp rules (D-018, D-022, U14)
// `state` is the participation after the requested change is applied.
function "pmf/survey/validate_response" {
  description = "Validate a participation's invitation and response state"
  input {
    json wave
    json state
  }

  stack {
    var $s {
      value = $input.state
    }

    var $limit {
      value = now|transform_timestamp:"+5 minutes"
    }

    var $has_answers {
      value = $s.disappointment_level != null || $s.beneficiary_description != null || $s.main_benefit != null || $s.improvement_request != null
    }

    precondition (!$has_answers || $s.responded_at != null) {
      error_type = "inputerror"
      error = "RESPONSE_STATE: a disappointment category or answer requires responded_at"
    }

    precondition ($s.invited_at == null || $s.invited_at <= $limit) {
      error_type = "inputerror"
      error = "INVALID_TIMESTAMP: invited_at is in the future"
    }

    conditional {
      if ($s.responded_at != null) {
        precondition ($input.wave.started_at != null) {
          error_type = "inputerror"
          error = "WAVE_NOT_STARTED: set the wave start before recording responses"
        }

        precondition ($s.responded_at >= $input.wave.started_at) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: responded_at is before the wave started"
        }

        precondition ($s.responded_at <= $limit) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: responded_at is in the future"
        }

        precondition ($s.invited_at == null || $s.invited_at <= $s.responded_at) {
          error_type = "inputerror"
          error = "INVALID_TIMESTAMP: invited_at is after responded_at"
        }
      }
    }
  }

  response = true

  test "category without responded_at is rejected" {
    input = {wave: {started_at: 1000}, state: {disappointment_level: "very", responded_at: null}}
    expect.to_throw
  }

  test "responded_at without category is allowed (incomplete)" {
    input = {wave: {started_at: 1000}, state: {responded_at: 2000, disappointment_level: null}}
    expect.to_be_true ($response)
  }

  test "response before wave start is rejected" {
    input = {wave: {started_at: 5000}, state: {responded_at: 2000, disappointment_level: "not"}}
    expect.to_throw
  }

  test "response on unstarted wave is rejected" {
    input = {wave: {started_at: null}, state: {responded_at: 2000, disappointment_level: "not"}}
    expect.to_throw
  }

  test "invitation after response is rejected" {
    input = {wave: {started_at: 1000}, state: {invited_at: 3000, responded_at: 2000, disappointment_level: "somewhat"}}
    expect.to_throw
  }

  test "valid historical response passes" {
    input = {wave: {started_at: 1000}, state: {invited_at: 1500, responded_at: 2000, disappointment_level: "very", main_benefit: "speed"}}
    expect.to_be_true ($response)
  }
  guid = "Pa3AIbNrZ8QT8odb2VJUxgypZw0"
}
