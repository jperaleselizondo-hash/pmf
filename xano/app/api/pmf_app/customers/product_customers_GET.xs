// PMF Engine: search and filter a product's customers (no interview or survey text in this list)
query "products/{product_id}/customers" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List customers of a product"
  input {
    int product_id
    text? q? filters=trim
    int? segment_id?
    enum? lifecycle_stage? {
      values = ["prospect", "active", "former"]
    }

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

    function.run "pmf/text/normalize" {
      input = {value: $input.q}
    } as $q

    conditional {
      if ($q == null) {
        db.query customers {
          where = $db.customers.product_id == $product.id && $db.customers.segment_id ==? $input.segment_id && $db.customers.lifecycle_stage ==? $input.lifecycle_stage
          sort = {created_at: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
        } as $customers
      }

      else {
        db.query customers {
          where = $db.customers.product_id == $product.id && $db.customers.segment_id ==? $input.segment_id && $db.customers.lifecycle_stage ==? $input.lifecycle_stage && ($db.customers.name includes $q || $db.customers.email includes $q || $db.customers.company_name includes $q || $db.customers.external_id includes $q)
          sort = {created_at: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
        } as $customers
      }
    }
  }

  response = $customers
}
