// PMF Engine: list the owner's products
query "products" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List products owned by the designated owner"
  input {
    int page?=1 filters=min:1
    int per_page?=25 filters=min:1|max:100
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    db.query products {
      where = $db.products.owner_user_id == $auth.id
      sort = {created_at: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $products
  }

  response = $products
  guid = "kED2FiQ63Q7ac8X7KysAllWFOFo"
}
