// PMF Engine: PMF % = 100 * very / valid responses; null when there are no valid responses (pure)
// Invited response rate counts only valid responses from invited participants.
function "pmf/report/compute_pmf" {
  description = "Compute PMF percentage, distribution and invited response rate from counts"
  input {
    json counts
    int small_sample_threshold?=30
  }

  stack {
    var $c {
      value = $input.counts
    }

    var $valid {
      value = $c.valid_response_count|to_decimal
    }

    // Runtime fix (2026-10-23): the former inline `((x|to_decimal) * 100) / $valid` expressions failed on the
    // server with "Array to string conversion". Each percentage is now built in single steps with the
    // documented math filters, and the distribution object only holds plain variables.
    var $pmf {
      value = null
    }

    var $pct_somewhat {
      value = null
    }

    var $pct_not {
      value = null
    }

    conditional {
      if ($c.valid_response_count > 0) {
        var $very_dec {
          value = $c.very_count|to_decimal
        }

        var $somewhat_dec {
          value = $c.somewhat_count|to_decimal
        }

        var $not_dec {
          value = $c.not_count|to_decimal
        }

        var.update $pmf {
          value = $very_dec|divide:$valid
        }

        var.update $pmf {
          value = $pmf|multiply:100
        }

        var.update $pct_somewhat {
          value = $somewhat_dec|divide:$valid
        }

        var.update $pct_somewhat {
          value = $pct_somewhat|multiply:100
        }

        var.update $pct_not {
          value = $not_dec|divide:$valid
        }

        var.update $pct_not {
          value = $pct_not|multiply:100
        }
      }
    }

    var $dist {
      value = {very: $pmf, somewhat: $pct_somewhat, not: $pct_not}
    }

    var $rate {
      value = null
    }

    conditional {
      if ($c.invited_count > 0) {
        var.update $rate {
          value = ($c.invited_valid_count|to_decimal) / ($c.invited_count|to_decimal)
        }
      }
    }
  }

  response = {
    eligible_count           : $c.eligible_count
    invited_count            : $c.invited_count
    responded_count          : $c.responded_count
    valid_response_count     : $c.valid_response_count
    incomplete_response_count: $c.incomplete_response_count
    anomaly_count            : $c.anomaly_count
    counts                   : {very: $c.very_count, somewhat: $c.somewhat_count, not: $c.not_count}
    pmf_percent              : $pmf
    distribution_percent     : $dist
    invited_valid_count      : $c.invited_valid_count
    manual_valid_count       : $c.manual_valid_count
    invited_response_rate    : $rate
    response_rate_denominator: "invited_count"
    small_sample             : $c.valid_response_count < $input.small_sample_threshold
  }

  test "fixture: 1 very of 3 valid is 33.333 percent, not truncated" {
    input = {
      counts: {eligible_count: 5, invited_count: 4, responded_count: 3, valid_response_count: 3, incomplete_response_count: 0, anomaly_count: 0, very_count: 1, somewhat_count: 1, not_count: 1, invited_valid_count: 2, manual_valid_count: 1}
    }

    expect.to_be_within ($response.pmf_percent) {
      min = 33.3333
      max = 33.3334
    }

    expect.to_equal ($response.invited_response_rate) {
      value = 0.5
    }

    expect.to_be_true ($response.small_sample)
  }

  test "zero valid responses gives null, not zero" {
    input = {
      counts: {eligible_count: 1, invited_count: 0, responded_count: 0, valid_response_count: 0, incomplete_response_count: 0, anomaly_count: 0, very_count: 0, somewhat_count: 0, not_count: 0, invited_valid_count: 0, manual_valid_count: 0}
    }

    expect.to_be_null ($response.pmf_percent)
    expect.to_be_null ($response.invited_response_rate)
  }

  test "zero very of one valid is 0.0, not null" {
    input = {
      counts: {eligible_count: 1, invited_count: 0, responded_count: 1, valid_response_count: 1, incomplete_response_count: 0, anomaly_count: 0, very_count: 0, somewhat_count: 0, not_count: 1, invited_valid_count: 0, manual_valid_count: 1}
    }

    expect.to_equal ($response.pmf_percent) {
      value = 0
    }
  }

  test "two very of three valid is 66.666 percent" {
    input = {
      counts: {eligible_count: 3, invited_count: 3, responded_count: 3, valid_response_count: 3, incomplete_response_count: 0, anomaly_count: 0, very_count: 2, somewhat_count: 1, not_count: 0, invited_valid_count: 3, manual_valid_count: 0}
    }

    expect.to_be_within ($response.pmf_percent) {
      min = 66.6666
      max = 66.6667
    }
  }

  test "distribution percentages use the valid-response denominator" {
    input = {
      counts: {eligible_count: 5, invited_count: 4, responded_count: 3, valid_response_count: 3, incomplete_response_count: 0, anomaly_count: 0, very_count: 1, somewhat_count: 1, not_count: 1, invited_valid_count: 2, manual_valid_count: 1}
    }

    expect.to_be_within ($response.distribution_percent.very) {
      min = 33.3333
      max = 33.3334
    }

    expect.to_be_within ($response.distribution_percent.somewhat) {
      min = 33.3333
      max = 33.3334
    }

    expect.to_be_within ($response.distribution_percent.not) {
      min = 33.3333
      max = 33.3334
    }
  }

  test "one very of seven valid is not truncated" {
    input = {
      counts: {eligible_count: 7, invited_count: 0, responded_count: 7, valid_response_count: 7, incomplete_response_count: 0, anomaly_count: 0, very_count: 1, somewhat_count: 3, not_count: 3, invited_valid_count: 0, manual_valid_count: 7}
    }

    expect.to_be_within ($response.pmf_percent) {
      min = 14.2857
      max = 14.2858
    }

    expect.to_be_null ($response.invited_response_rate)
  }

  test "zero valid gives null distribution and a zero invited rate when invited" {
    input = {
      counts: {eligible_count: 4, invited_count: 4, responded_count: 0, valid_response_count: 0, incomplete_response_count: 0, anomaly_count: 0, very_count: 0, somewhat_count: 0, not_count: 0, invited_valid_count: 0, manual_valid_count: 0}
    }

    expect.to_be_null ($response.pmf_percent)
    expect.to_be_null ($response.distribution_percent.very)
    expect.to_be_null ($response.distribution_percent.not)
    expect.to_equal ($response.invited_response_rate) {
      value = 0
    }
  }
  guid = "AEGp_SqbtyKw6O5hh5ZXHQIhqHk"
}
