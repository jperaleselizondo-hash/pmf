// PMF Engine: list a product's survey waves with state and eligible counts
query "products/{product_id}/survey-waves" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "List survey waves of a product"
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

    db.query survey_waves {
      where = $db.survey_waves.product_id == $product.id
      sort = {created_at: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $page

    var $items {
      value = []
    }

    foreach ($page.items) {
      each as $wave {
        function.run "pmf/survey/wave_state" {
          input = {wave: $wave}
        } as $state

        db.query survey_participations {
          where = $db.survey_participations.survey_wave_id == $wave.id
          return = {type: "count"}
        } as $eligible

        var $row {
          value = $wave|set:"state":($state)
        }

        var.update $row {
          value = $row|set:"eligible_count":($eligible)
        }

        var.update $items {
          value = $items|push:($row)
        }
      }
    }
  }

  response = $page|set:"items":$items
  guid = "-_mAXufnbCy_ulkaTVqOVubyCVo"
}
