import { describe, expect, it } from 'vitest';
import { truncateCodePoints } from '../src/text.js';

const UNPAIRED_SURROGATE =
  /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

describe('truncateCodePoints', () => {
  it('returns text shorter than the cap unchanged, not truncated', () => {
    const result = truncateCodePoints('hello', 300);
    expect(result).toEqual({ text: 'hello', truncated: false, total: 5 });
  });

  it('does not truncate text exactly at the cap (strict > boundary)', () => {
    const text = 'abcde';
    const result = truncateCodePoints(text, text.length);
    expect(result.truncated).toBe(false);
    expect(result.text).toBe(text);
    expect(result.total).toBe(5);
  });

  it('never splits a surrogate pair, at a cap where naive slice would', () => {
    // 5 ASCII chars (1 code unit / code point each) followed by three
    // astral emoji (2 code units each, 1 code point each): 8 code points
    // total, 11 UTF-16 code units total.
    const text = 'aaaaa' + '📊' + '🔴' + '🔵';
    const cap = 6;

    // Prove the naive bug this replaces really would fire at this cap:
    // slicing by UTF-16 code unit with the same number used as a code-point
    // cap keeps the 5 ASCII chars plus only the high surrogate of 📊 —
    // an unpaired surrogate.
    const naive = text.slice(0, cap);
    expect(UNPAIRED_SURROGATE.test(naive)).toBe(true);

    const result = truncateCodePoints(text, cap);
    expect(result.truncated).toBe(true);
    expect(UNPAIRED_SURROGATE.test(result.text)).toBe(false);
    expect(result.text).toBe('aaaaa📊');
    expect(result.total).toBe(8); // 5 ASCII + 3 astral code points, not 11 code units
  });

  it('counts by code point, not code unit', () => {
    const astral = '📊🔴🔵'; // 3 code points, 6 UTF-16 code units
    expect(Array.from(astral).length).toBe(3);
    expect(astral.length).toBe(6);

    // Cap set to the code-point count: must not be truncated.
    const atCap = truncateCodePoints(astral, 3);
    expect(atCap.truncated).toBe(false);
    expect(atCap.text).toBe(astral);
    expect(atCap.total).toBe(3);

    // Cap set below the code-point count: must truncate on a code-point
    // boundary, not a code-unit boundary.
    const belowCap = truncateCodePoints(astral, 2);
    expect(belowCap.truncated).toBe(true);
    expect(belowCap.text).toBe('📊🔴');
    expect(UNPAIRED_SURROGATE.test(belowCap.text)).toBe(false);
    expect(belowCap.total).toBe(3); // total counts the whole input, not the truncated output
  });

  it('reports the same total whether or not truncation happens', () => {
    // `total` is the input's code-point count, independent of `max` — it
    // must not silently become the *returned* text's length once truncation
    // kicks in (that would defeat get_document.ts's total_chars use, which
    // needs the pre-truncation size to report how much was cut).
    const text = 'abcdefghij';
    expect(truncateCodePoints(text, 3).total).toBe(10);
    expect(truncateCodePoints(text, 100).total).toBe(10);
  });
});
