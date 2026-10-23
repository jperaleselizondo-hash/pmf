// PMF Engine: create a survey wave with its fixed eligibility rule and questionnaire version
query "products/{product_id}/survey-waves" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create a survey wave"
  input {
    int product_id
    text name filters=trim
    text eligibility_rule filters=trim
    text questionnaire_version filters=trim
    timestamp? started_at?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    function.run "pmf/util/patch_data" {
      input = {
        values  : {name: $input.name, eligibility_rule: $input.eligibility_rule, questionnaire_version: $input.questionnaire_version}
        required: ["name", "eligibility_rule", "questionnaire_version"]
        touch   : false
      }
    } as $data

    db.add survey_waves {
      data = {
        product_id           : $product.id
        name                 : $data|get:"name"
        eligibility_rule     : $data|get:"eligibility_rule"
        questionnaire_version: $data|get:"questionnaire_version"
        started_at           : $input.started_at
        closed_at            : null
      }
    } as $wave
  }

  response = $wave
  guid = "yPUcq-6rMqDaWh6rIwds8kvhHuA"
}
