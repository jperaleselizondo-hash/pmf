// PMF Engine: eligible / invited / valid / incomplete / anomaly
function "pmf/survey/participation_status" {
  description = "Classify a survey participation"
  input {
    json participation
  }

  stack {
    var $p {
      value = $input.participation
    }

    var $status {
      value = "eligible"
    }

    conditional {
      if ($p.responded_at == null && $p.disappointment_level != null) {
        var.update $status {
          value = "anomaly"
        }
      }

      elseif ($p.responded_at != null && $p.disappointment_level != null) {
        var.update $status {
          value = "valid"
        }
      }

      elseif ($p.responded_at != null) {
        var.update $status {
          value = "incomplete"
        }
      }

      elseif ($p.invited_at != null) {
        var.update $status {
          value = "invited"
        }
      }
    }
  }

  response = $status

  test "valid" {
    input = {participation: {invited_at: 1, responded_at: 2, disappointment_level: "very"}}
    expect.to_equal ($response) {
      value = "valid"
    }
  }

  test "incomplete" {
    input = {participation: {responded_at: 2, disappointment_level: null}}
    expect.to_equal ($response) {
      value = "incomplete"
    }
  }

  test "invited" {
    input = {participation: {invited_at: 1, responded_at: null, disappointment_level: null}}
    expect.to_equal ($response) {
      value = "invited"
    }
  }

  test "eligible" {
    input = {participation: {invited_at: null, responded_at: null, disappointment_level: null}}
    expect.to_equal ($response) {
      value = "eligible"
    }
  }

  test "anomaly" {
    input = {participation: {responded_at: null, disappointment_level: "not"}}
    expect.to_equal ($response) {
      value = "anomaly"
    }
  }
}
