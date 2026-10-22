// PMF Engine: serialize writes on one survey wave (PROVISIONAL, U13)
// Call first inside db.transaction. A no-op self-update is expected to hold the row lock until commit;
// this must be proven by isolated concurrency tests C01/C03 before deployment.
function "pmf/lock/wave" {
  description = "Lock a survey wave row and return its current state"
  input {
    int wave_id
  }

  stack {
    db.get survey_waves {
      field_name = "id"
      field_value = $input.wave_id
    } as $wave

    precondition ($wave != null) {
      error_type = "notfound"
      error = "NOT_FOUND: survey wave not found"
    }

    db.edit survey_waves {
      field_name = "id"
      field_value = $input.wave_id
      data = {name: $wave.name}
    } as $locked
  }

  response = $locked
}
