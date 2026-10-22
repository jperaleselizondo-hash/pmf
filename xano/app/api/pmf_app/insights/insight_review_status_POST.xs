// PMF Engine: explicit review transition; reviewed requires valid evidence; back to draft blocked by hypotheses (U6)
query "insights/{insight_id}/review-status" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Set an insight's review status"
  input {
    int insight_id
    enum review_status {
      values = ["draft", "reviewed"]
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/insight" {
      input = {insight_id: $input.insight_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $input.insight_id}
        } as $insight

        precondition ($insight.review_status != $input.review_status) {
          error_type = "inputerror"
          error = "NO_STATUS_CHANGE: the insight already has this review status"
        }

        conditional {
          if ($input.review_status == "reviewed") {
            function.run "pmf/insight/count_valid_evidence" {
              input = {insight_id: $input.insight_id}
            } as $valid_evidence

            precondition ($valid_evidence > 0) {
              error_type = "inputerror"
              error = "EVIDENCE_REQUIRED: a reviewed insight needs at least one valid evidence link"
            }
          }

          else {
            db.query hypotheses {
              where = $db.hypotheses.insight_id == $input.insight_id
              return = {type: "count"}
            } as $hypothesis_count

            precondition ($hypothesis_count == 0) {
              error_type = "inputerror"
              error = "INSIGHT_HAS_HYPOTHESES: an insight with hypotheses must stay reviewed"
            }
          }
        }

        db.edit insights {
          field_name = "id"
          field_value = $input.insight_id
          data = {review_status: $input.review_status, updated_at: now}
        } as $updated
      }
    }
  }

  response = $updated
}
