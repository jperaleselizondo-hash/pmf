// PMF Engine: PMF report for a wave; optional filter by snapshot segment or unsegmented participants
query "survey-waves/{wave_id}/report" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "PMF report for a survey wave"
  input {
    int wave_id
    int? segment_id?
    bool unsegmented?=false
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/wave" {
      input = {wave_id: $input.wave_id, auth_id: $auth.id}
    } as $access

    precondition (!($input.segment_id != null && $input.unsegmented)) {
      error_type = "inputerror"
      error = "INVALID_INPUT: use either segment_id or unsegmented, not both"
    }

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $access.product_id}
    } as $segment

    function.run "pmf/report/build_wave_report" {
      input = {wave: $access.record, segment_id: $input.segment_id, unsegmented: $input.unsegmented, summary: false}
    } as $report
  }

  response = $report
  guid = "ddCi1ngbq5_N8mpqU0Y0b-1n8Fk"
}
