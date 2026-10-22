// PMF Engine: list a product's hypotheses (resolved through their insights) with experiment counts
query "products/{product_id}/hypotheses" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List hypotheses of a product"
  input {
    int product_id
    enum? status? {
      values = ["proposed", "testing", "validated", "rejected"]
    }

    enum? priority? {
      values = ["low", "medium", "high"]
    }

    int? insight_id?
    int page?=1 filters=min:1
    int per_page?=25 filters=min:1|max:100
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    db.query hypotheses {
      join = {
        insights: {table: "insights", type: "inner", where: $db.hypotheses.insight_id == $db.insights.id}
      }

      where = $db.insights.product_id == $product.id && $db.hypotheses.status ==? $input.status && $db.hypotheses.priority ==? $input.priority && $db.hypotheses.insight_id ==? $input.insight_id
      sort = {created_at: "desc"}
      eval = {insight_statement: $db.insights.statement}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $page

    var $items {
      value = []
    }

    foreach ($page.items) {
      each as $hypothesis {
        db.query experiments {
          where = $db.experiments.hypothesis_id == $hypothesis.id
          return = {type: "count"}
        } as $experiment_count

        var $insight_summary {
          value = {id: $hypothesis.insight_id, statement: $hypothesis.insight_statement}
        }

        var $row {
          value = $hypothesis|set:"insight":($insight_summary)
        }

        var.update $row {
          value = $row|set:"experiment_count":($experiment_count)
        }

        var.update $items {
          value = $items|push:($row)
        }
      }
    }
  }

  response = $page|set:"items":$items
}
