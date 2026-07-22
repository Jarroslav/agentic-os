/** Truncate to at most `max` Unicode code points, never splitting a surrogate
 *  pair. Returns the text unchanged when it already fits. */
export function truncateCodePoints(
  text: string,
  max: number,
): { text: string; truncated: boolean } {
  const codePoints = Array.from(text);
  if (codePoints.length <= max) return { text, truncated: false };
  return { text: codePoints.slice(0, max).join(''), truncated: true };
}
