// PMF Engine: load a survey participation whose wave's product is owned by the caller, or 404
function "pmf/access/participation" {
  description = "Load an owned survey participation"
  input {
    int participation_id
    int auth_id
  }

  stack {
    db.get survey_participations {
      field_name = "id"
      field_value = $input.participation_id
    } as $participation

    precondition ($participation != null) {
      error_type = "notfound"
      error = "NOT_FOUND: participation not found"
    }

    function.run "pmf/access/wave" {
      input = {wave_id: $participation.survey_wave_id, auth_id: $input.auth_id}
    } as $wave
  }

  response = {record: $participation, wave: $wave.record, product_id: $wave.product_id}
}
