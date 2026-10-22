// PMF Engine: a PMF survey round with fixed eligibility and questionnaire
table survey_waves {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int product_id {
      table = "products"
    }

    text name filters=trim
    text eligibility_rule filters=trim {
      description = "Fixed for the wave; API must block edits once participations exist"
    }

    text questionnaire_version filters=trim {
      description = "Fixed for the wave; API must block edits once participations exist"
    }

    timestamp? started_at?
    timestamp? closed_at? {
      description = "Set when the wave is closed; API blocks participation and response edits afterwards"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "product_id", op: "asc"}, {name: "started_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
