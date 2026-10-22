// PMF Engine: update a segment (product immutable; renaming never alters participation snapshots)
query "segments/{segment_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update a segment"
  input {
    int segment_id
    text? name? filters=trim
    text? description? filters=trim
    text? criteria? filters=trim
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/segment" {
      input = {segment_id: $input.segment_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values  : {name: $input.name, description: $input.description, criteria: $input.criteria}
        required: ["name"]
      }
    } as $data

    conditional {
      if ($input.name != null && $input.name != $access.record.name) {
        db.query segments {
          where = $db.segments.product_id == $access.product_id && $db.segments.name == $input.name && $db.segments.id != $input.segment_id
          return = {type: "exists"}
        } as $duplicate

        precondition (!$duplicate) {
          error_type = "inputerror"
          error = "DUPLICATE_SEGMENT_NAME: a segment with this name already exists for the product"
        }
      }
    }

    db.patch segments {
      field_name = "id"
      field_value = $input.segment_id
      data = $data
    } as $updated
  }

  response = $updated
}
