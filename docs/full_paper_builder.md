# Full-paper parsing contract

`FullPaperBuilder` targets MathonGo-style JEE Main papers with continuous
`Q<n>.` numbering and an answer key after the paper body. It is deterministic:
it extracts only text, equations, and images that MinerU produced.

## Stages

1. Filter removes deterministic headers, watermarks, and page numbers while
   retaining source index and page provenance.
2. Segment separates the paper body from the final answer-key section.
3. Group assigns consecutive body blocks to the currently open question.
4. Build creates the existing `Question` dataclass and preserves partial
   option recovery as warnings.
5. Validate/merge attaches a key answer only when an entry was extracted.

## Review warnings

Warnings are intentionally part of the ingestion report. They cover missing
options, missing answer-key entries, repeated question numbers, conflicting
option text, and image files MinerU referenced but did not produce.

## MinerU limitations observed in this layout

- A question marker can be OCR'd incorrectly (for example `Q72.` becoming
  `Q 7 2 .` or `74.` becoming `4.`). The parser reports gaps/duplicates; it
  does not infer the missing digit.
- A diagram may be emitted as a separate image block. It is linked only when
  the referenced image file exists; missing files remain a warning.
- Options can appear in text blocks, equation arrays, or as merged `(13)` /
  `(24)` markers. If two readings disagree, the first reading-order value is
  retained and the conflict is flagged rather than overwritten.
- In the supplied 22 Jan Shift 1 paper, the source PDF has `ANSWER KEYS` on
  page 14 in the form `1. (4)`. MinerU's corresponding output represents that
  page as an image block and supplies no key text. The builder emits an
  explicit stage warning and does not fabricate answers. A deterministic OCR
  fallback, if adopted later, belongs upstream of this builder and must retain
  page/image provenance plus a review status.

The test suite uses small block sequences for every parsing rule. Add a
minimized block fixture for each newly observed MinerU layout variation before
adding a parser rule.
