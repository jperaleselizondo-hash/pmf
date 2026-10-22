// PMF Engine: list a product's segments with current customer counts
query "products/{product_id}/segments" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List segments of a product"
  input {
    int product_id
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

    db.query segments {
      where = $db.segments.product_id == $product.id
      sort = {name: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $page

    var $items {
      value = []
    }

    foreach ($page.items) {
      each as $segment {
        db.query customers {
          where = $db.customers.segment_id == $segment.id
          return = {type: "count"}
        } as $segment_customers

        var.update $items {
          value = $items|push:($segment|set:"customer_count":$segment_customers)
        }
      }
    }
  }

  response = $page|set:"items":$items
}
