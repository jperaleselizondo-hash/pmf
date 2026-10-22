// PMF Engine: list a product's insights with evidence and hypothesis counts
query "products/{product_id}/insights" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List insights of a product"
  input {
    int product_id
    enum? type? {
      values = ["problem", "benefit", "obstacle", "customer_characteristic"]
    }

    enum? review_status? {
      values = ["draft", "reviewed"]
    }

    enum? confidence? {
      values = ["low", "medium", "high"]
    }

    int? segment_id?
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

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $product.id}
    } as $segment

    db.query insights {
      where = $db.insights.product_id == $product.id && $db.insights.type ==? $input.type && $db.insights.review_status ==? $input.review_status && $db.insights.confidence ==? $input.confidence && $db.insights.segment_id ==? $input.segment_id
      sort = {created_at: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $page

    var $items {
      value = []
    }

    foreach ($page.items) {
      each as $insight {
        db.query insight_evidence {
          where = $db.insight_evidence.insight_id == $insight.id && $db.insight_evidence.relationship == "supports"
          return = {type: "count"}
        } as $supports

        db.query insight_evidence {
          where = $db.insight_evidence.insight_id == $insight.id && $db.insight_evidence.relationship == "contradicts"
          return = {type: "count"}
        } as $contradicts

        db.query hypotheses {
          where = $db.hypotheses.insight_id == $insight.id
          return = {type: "count"}
        } as $hypothesis_count

        var.update $items {
          value = $items|push:($insight|set:"evidence_count":{supports: $supports, contradicts: $contradicts}|set:"hypothesis_count":$hypothesis_count)
        }
      }
    }
  }

  response = $page|set:"items":$items
}
