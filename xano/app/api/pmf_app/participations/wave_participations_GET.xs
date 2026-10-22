// PMF Engine: participants of a wave with status, filterable by status and snapshot segment
query "survey-waves/{wave_id}/participations" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List participations of a survey wave"
  input {
    int wave_id
    enum? status? {
      values = ["eligible", "invited", "responded", "valid", "incomplete", "anomaly"]
    }

    int? segment_id?
    bool unsegmented?=false
    int page?=1 filters=min:1
    int per_page?=25 filters=min:1|max:100
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $access.product_id}
    } as $segment

    db.query survey_participations {
      join = {
        customers: {table: "customers", type: "inner", where: $db.survey_participations.customer_id == $db.customers.id}
      }

      where = $db.survey_participations.survey_wave_id == $input.wave_id
      sort = {created_at: "asc"}
      eval = {customer_name: $db.customers.name, customer_external_id: $db.customers.external_id}
      return = {type: "list"}
    } as $rows

    var $filtered {
      value = []
    }

    foreach ($rows) {
      each as $row {
        function.run "pmf/survey/participation_status" {
          input = {participation: $row}
        } as $status

        var $keep {
          value = $input.status == null || $input.status == $status || ($input.status == "responded" && ($status == "valid" || $status == "incomplete"))
        }

        conditional {
          if ($input.segment_id != null && $row.segment_id_snapshot != $input.segment_id) {
            var.update $keep {
              value = false
            }
          }
        }

        conditional {
          if ($input.unsegmented && $row.segment_id_snapshot != null) {
            var.update $keep {
              value = false
            }
          }
        }

        conditional {
          if ($keep) {
            var.update $filtered {
              value = $filtered|push:{id: $row.id, customer: {id: $row.customer_id, name: $row.customer_name, external_id: $row.customer_external_id}, segment_id_snapshot: $row.segment_id_snapshot, invited_at: $row.invited_at, responded_at: $row.responded_at, disappointment_level: $row.disappointment_level, beneficiary_description: $row.beneficiary_description, main_benefit: $row.main_benefit, improvement_request: $row.improvement_request, status: $status, created_at: $row.created_at, updated_at: $row.updated_at}
            }
          }
        }
      }
    }

    var $offset {
      value = ($input.page - 1) * $input.per_page
    }

    var $items {
      value = $filtered|slice:$offset:($offset + $input.per_page)
    }
  }

  response = {items: $items, curPage: $input.page, perPage: $input.per_page, itemsTotal: $filtered|count}
}
