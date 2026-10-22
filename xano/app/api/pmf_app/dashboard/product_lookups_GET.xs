// PMF Engine: minimal id/label lists for pickers (capped at 500 per list)
query "products/{product_id}/lookups" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Picker lookups for a product"
  input {
    int product_id
    text[]? include?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    var $include {
      value = $input.include ?? ["segments", "customers", "waves", "interviews", "reviewed_insights"]
    }

    var $result {
      value = {}
    }

    conditional {
      if ($include|some:$$ == "segments") {
        db.query segments {
          where = $db.segments.product_id == $product.id
          sort = {name: "asc"}
          return = {type: "list", paging: {page: 1, per_page: 500}}
          output = ["id", "name"]
        } as $segments

        var.update $result {
          value = $result|set:"segments":$segments.items
        }
      }
    }

    conditional {
      if ($include|some:$$ == "customers") {
        db.query customers {
          where = $db.customers.product_id == $product.id
          sort = {name: "asc"}
          return = {type: "list", paging: {page: 1, per_page: 500}}
          output = ["id", "name", "external_id", "segment_id"]
        } as $customers

        var.update $result {
          value = $result|set:"customers":$customers.items
        }
      }
    }

    conditional {
      if ($include|some:$$ == "waves") {
        db.query survey_waves {
          where = $db.survey_waves.product_id == $product.id
          sort = {created_at: "desc"}
          return = {type: "list", paging: {page: 1, per_page: 500}}
          output = ["id", "name", "started_at", "closed_at"]
        } as $waves

        var.update $result {
          value = $result|set:"waves":$waves.items
        }
      }
    }

    conditional {
      if ($include|some:$$ == "interviews") {
        db.query interviews {
          join = {
            customers: {table: "customers", type: "inner", where: $db.interviews.customer_id == $db.customers.id}
          }

          where = $db.customers.product_id == $product.id
          sort = {conducted_at: "desc"}
          eval = {customer_name: $db.customers.name}
          return = {type: "list", paging: {page: 1, per_page: 500}}
          output = ["id", "customer_id", "conducted_at", "customer_name"]
        } as $interviews

        var.update $result {
          value = $result|set:"interviews":$interviews.items
        }
      }
    }

    conditional {
      if ($include|some:$$ == "reviewed_insights") {
        db.query insights {
          where = $db.insights.product_id == $product.id && $db.insights.review_status == "reviewed"
          sort = {created_at: "desc"}
          return = {type: "list", paging: {page: 1, per_page: 500}}
          output = ["id", "type", "statement"]
        } as $reviewed

        var.update $result {
          value = $result|set:"reviewed_insights":$reviewed.items
        }
      }
    }
  }

  response = $result
}
