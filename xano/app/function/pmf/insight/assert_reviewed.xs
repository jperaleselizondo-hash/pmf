// PMF Engine: hypotheses may only be linked to reviewed insights
function "pmf/insight/assert_reviewed" {
  description = "Reject non-reviewed insights"
  input {
    json insight
  }

  stack {
    precondition ($input.insight.review_status == "reviewed") {
      error_type = "inputerror"
      error = "INSIGHT_NOT_REVIEWED: hypotheses require a reviewed insight"
    }
  }

  response = true

  test "reviewed passes" {
    input = {insight: {review_status: "reviewed"}}
    expect.to_be_true ($response)
  }

  test "draft throws" {
    input = {insight: {review_status: "draft"}}
    expect.to_throw
  }
}
