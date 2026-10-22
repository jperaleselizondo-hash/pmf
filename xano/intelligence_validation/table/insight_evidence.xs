// PMF Engine: exact evidence source for an interpreted insight
table insight_evidence {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int insight_id {
      table = "insights"
    }

    int? interview_id? {
      table = "interviews"
      description = "Exactly one source FK: interview_id XOR survey_participation_id"
    }

    int? survey_participation_id? {
      table = "survey_participations"
      description = "Exactly one source FK: interview_id XOR survey_participation_id"
    }

    text? source_field? filters=trim {
      description = "Optional field-level provenance; validated free text, not an enum"
    }

    text excerpt {
      sensitive = true
      description = "Original evidence or clearly identified accurate summary; API must require meaningful text"
    }

    enum relationship {
      values = ["supports", "contradicts"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "insight_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "interview_id", op: "asc"}]}
    {type: "btree", field: [{name: "survey_participation_id", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
