// PMF Engine: delete a segment only when no customer, snapshot or insight references it
query "segments/{segment_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an unreferenced segment"
  input {
    int segment_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/segment" {
      input = {segment_id: $input.segment_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/guard/count_references" {
          input = {entity: "segment", id: $input.segment_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the segment is referenced by customers, survey snapshots or insights"
        }

        db.del segments {
          field_name = "id"
          field_value = $input.segment_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.segment_id}
}
