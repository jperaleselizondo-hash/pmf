// PMF Engine: evidence rows citing exactly one source (sources are immutable and deletion-protected)
function "pmf/insight/count_valid_evidence" {
  description = "Count valid evidence links for an insight"
  input {
    int insight_id
  }

  stack {
    db.query insight_evidence {
      where = $db.insight_evidence.insight_id == $input.insight_id
      return = {type: "list"}
      output = ["id", "interview_id", "survey_participation_id"]
    } as $rows

    var $valid {
      value = $rows|filter:($$.interview_id != null) != ($$.survey_participation_id != null)
    }
  }

  response = $valid|count
}
