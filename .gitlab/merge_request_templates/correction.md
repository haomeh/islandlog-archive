<!-- Fill in every field. Do not delete the two review fields. -->

## Correction

- Request (issue or suggestion link):
- Object IDs to correct:
- Correction type (`factual`, `attribution`, `source`, `privacy`):
- Correction record file: `corrections/<YYYY>/cr-YYYYMMDD-nn.yaml`

## MR review fields

Write exactly `true` or `false` after each colon. If `review_sensitive` is `true`, `review_reason` must not be empty.

review_sensitive:
review_reason:

## Verification steps (required)

Write how you checked the claim in the request and which official record or second source you used.

| Claim in the request | Method | Official record or second source |
|---|---|---|
| | | |

## Checklist

- [ ] The correction record is new. I did not change or delete an older record.
- [ ] Neutral wording. Claims are written as "X said ...".
- [ ] Source grades match the class table.
- [ ] The public summary does not repeat removed personal data.
- [ ] `islandlog validate .` passes on my machine.

/label ~correction
