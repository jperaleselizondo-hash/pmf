// PMF Engine: draft (not started), open, or closed
function "pmf/survey/wave_state" {
  description = "Derive survey wave state"
  input {
    json wave
  }

  stack {
    var $state {
      value = "open"
    }

    conditional {
      if ($input.wave.closed_at != null) {
        var.update $state {
          value = "closed"
        }
      }

      elseif ($input.wave.started_at == null || $input.wave.started_at > now) {
        var.update $state {
          value = "draft"
        }
      }
    }
  }

  response = $state

  test "closed wins" {
    input = {wave: {started_at: 1000, closed_at: 2000}}
    expect.to_equal ($response) {
      value = "closed"
    }
  }

  test "no start is draft" {
    input = {wave: {started_at: null, closed_at: null}}
    expect.to_equal ($response) {
      value = "draft"
    }
  }

  test "started and not closed is open" {
    input = {wave: {started_at: 1000, closed_at: null}}
    expect.to_equal ($response) {
      value = "open"
    }
  }
  guid = "EoqBoaHFanPlD8i5X-NI5NJwgfE"
}
