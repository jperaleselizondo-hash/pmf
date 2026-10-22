// PMF Engine: update an insight; reviewed type/statement edits revert to draft, blocked if hypotheses exist (U5)
query "insights/{insight_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update an insight"
  input {
    int insight_id
    enum? type? {
      values = ["problem", "benefit", "obstacle", "customer_characteristic"]
    }

    text? statement? filters=trim {
      sensitive = true
    }

    enum? confidence? {
      values = ["low", "medium", "high"]
    }

    int? segment_id?
    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/insight" {
      input = {insight_id: $input.insight_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $access.product_id}
    } as $segment

    function.run "pmf/util/patch_data" {
      input = {
        values   : {type: $input.type, statement: $input.statement, confidence: $input.confidence, segment_id: $input.segment_id}
        clear    : $input.clear
        clearable: ["segment_id"]
        required : ["statement"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $input.insight_id}
        } as $insight

        var $content_change {
          value = ($input.type != null && $input.type != $insight.type) || ($input.statement != null && $input.statement != $insight.statement)
        }

        var $changes {
          value = $data
        }

        conditional {
          if ($insight.review_status == "reviewed" && $content_change) {
            db.query hypotheses {
              where = $db.hypotheses.insight_id == $input.insight_id
              return = {type: "count"}
            } as $hypothesis_count

            precondition ($hypothesis_count == 0) {
              error_type = "inputerror"
              error = "INSIGHT_HAS_HYPOTHESES: a reviewed insight with hypotheses cannot change its type or statement"
            }

            var.update $changes {
              value = $changes|set:"review_status":"draft"
            }
          }
        }

        db.patch insights {
          field_name = "id"
          field_value = $input.insight_id
          data = $changes
        } as $updated
      }
    }
  }

  response = $updated
}
