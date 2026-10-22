// PMF Engine: closed waves are read-only until explicitly reopened (D-021)
function "pmf/survey/assert_wave_open" {
  description = "Reject writes to a closed survey wave"
  input {
    json wave
  }

  stack {
    precondition ($input.wave.closed_at == null) {
      error_type = "inputerror"
      error = "WAVE_CLOSED: the survey wave is closed; reopen it explicitly to make corrections"
    }
  }

  response = true

  test "open wave passes" {
    input = {wave: {closed_at: null}}
    expect.to_be_true ($response)
  }

  test "closed wave throws" {
    input = {wave: {closed_at: 1000}}
    expect.to_throw
  }
  guid = "GPLb7Ktw2xZ2v5RSorEgqGI0Okk"
}
