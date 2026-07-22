/** Truncate to at most `max` Unicode code points, never splitting a surrogate
 *  pair. Returns the text unchanged when it already fits. `total` is the
 *  input's full code-point count (not the returned text's) — callers that
 *  need it (e.g. get_document.ts's `total_chars`) get it for free from the
 *  same `Array.from()` pass this function already does, instead of having
 *  to materialize the code-point array a second time themselves. */
export function truncateCodePoints(
  text: string,
  max: number,
): { text: string; truncated: boolean; total: number } {
  const codePoints = Array.from(text);
  if (codePoints.length <= max) return { text, truncated: false, total: codePoints.length };
  return { text: codePoints.slice(0, max).join(''), truncated: true, total: codePoints.length };
}
