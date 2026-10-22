// PMF Engine: remove an evidence link; a reviewed insight must keep at least one valid evidence link
query "evidence/{evidence_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an evidence link"
  input {
    int evidence_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/evidence" {
      input = {evidence_id: $input.evidence_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.record.insight_id}
        } as $insight

        conditional {
          if ($insight.review_status == "reviewed") {
            function.run "pmf/insight/count_valid_evidence" {
              input = {insight_id: $insight.id}
            } as $valid_evidence

            precondition ($valid_evidence > 1) {
              error_type = "inputerror"
              error = "LAST_EVIDENCE_OF_REVIEWED_INSIGHT: move the insight back to draft before removing its last evidence"
            }
          }
        }

        db.del insight_evidence {
          field_name = "id"
          field_value = $input.evidence_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.evidence_id}
}
