// PMF Engine: hypothesis status transitions (Appendix R3.1); statuses never change automatically
function "pmf/validation/validate_hypothesis_status" {
  description = "Validate a hypothesis status transition against its experiments"
  input {
    text current
    text next
    json experiments
  }

  stack {
    var $exps {
      value = $input.experiments ?? []
    }

    var $has_any {
      value = ($exps|count) > 0
    }

    var $has_supported {
      value = $exps|some:$$.conclusion == "supported"
    }

    var $has_refuted {
      value = $exps|some:$$.conclusion == "refuted"
    }

    var $ok {
      value = $input.current == $input.next
    }

    conditional {
      if ($input.current != $input.next) {
        conditional {
          if ($input.next == "testing") {
            var.update $ok {
              value = $has_any
            }
          }

          elseif ($input.next == "validated") {
            var.update $ok {
              value = $input.current == "testing" && $has_supported
            }
          }

          elseif ($input.next == "rejected") {
            var.update $ok {
              value = $input.current == "proposed" || ($input.current == "testing" && $has_refuted)
            }
          }

          elseif ($input.next == "proposed") {
            var.update $ok {
              value = !$has_any
            }
          }
        }
      }
    }

    precondition ($ok) {
      error_type = "inputerror"
      error = "INVALID_STATUS_TRANSITION: " ~ $input.current ~ " -> " ~ $input.next ~ " is not allowed with the recorded experiments"
    }
  }

  response = true

  test "proposed to testing needs an experiment" {
    input = {current: "proposed", next: "testing", experiments: []}
    expect.to_throw
  }

  test "proposed to validated is not allowed" {
    input = {current: "proposed", next: "validated", experiments: [{conclusion: "supported"}]}
    expect.to_throw
  }

  test "testing to validated needs a supported experiment" {
    input = {current: "testing", next: "validated", experiments: [{conclusion: "refuted"}]}
    expect.to_throw
  }

  test "testing to validated with supported passes" {
    input = {current: "testing", next: "validated", experiments: [{conclusion: "supported"}]}
    expect.to_be_true ($response)
  }

  test "proposed to rejected (abandoned) passes" {
    input = {current: "proposed", next: "rejected", experiments: []}
    expect.to_be_true ($response)
  }

  test "testing to rejected needs a refuted experiment" {
    input = {current: "testing", next: "rejected", experiments: [{conclusion: "inconclusive"}]}
    expect.to_throw
  }

  test "validated back to testing (re-test) passes" {
    input = {current: "validated", next: "testing", experiments: [{conclusion: "supported"}]}
    expect.to_be_true ($response)
  }

  test "back to proposed requires no experiments" {
    input = {current: "testing", next: "proposed", experiments: [{conclusion: null}]}
    expect.to_throw
  }
}
