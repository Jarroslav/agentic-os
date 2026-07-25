import { describe, expect, it } from 'vitest';
import {
  isResourceMatch,
  checkPermission,
} from '../scripts/check-registry-permission.mjs';

// Covers the release preflight added to close CRITICAL 1: the Registry
// grants permission on the raw, case-sensitive OIDC repository_owner claim
// (io.github.<owner>/*), and isResourceMatch here must reproduce upstream's
// internal/auth/jwt.go exactly -- a prefix match with no normalization -- so
// this check catches a namespace-case mismatch before npm publish runs
// rather than after.

describe('isResourceMatch (mirrors upstream internal/auth/jwt.go)', () => {
  it('matches a wildcard prefix pattern', () => {
    expect(isResourceMatch('io.github.Jarroslav/agentic-os', 'io.github.Jarroslav/*')).toBe(true);
  });

  it('is case-sensitive: lowercase grant does not cover a capitalized name', () => {
    expect(isResourceMatch('io.github.Jarroslav/agentic-os', 'io.github.jarroslav/*')).toBe(false);
  });

  it('is case-sensitive the other way too', () => {
    expect(isResourceMatch('io.github.jarroslav/agentic-os', 'io.github.Jarroslav/*')).toBe(false);
  });

  it('matches an exact (non-wildcard) pattern only exactly', () => {
    expect(isResourceMatch('io.github.Jarroslav/agentic-os', 'io.github.Jarroslav/agentic-os')).toBe(true);
    expect(isResourceMatch('io.github.Jarroslav/agentic-os-2', 'io.github.Jarroslav/agentic-os')).toBe(false);
  });

  it('does not match an unrelated namespace', () => {
    expect(isResourceMatch('io.github.Jarroslav/agentic-os', 'io.github.someoneelse/*')).toBe(false);
  });
});

describe('checkPermission', () => {
  it('finds a covering publish permission', () => {
    const matches = checkPermission('io.github.Jarroslav/agentic-os', [
      { action: 'publish', resource: 'io.github.Jarroslav/*' },
    ]);
    expect(matches).toHaveLength(1);
  });

  it('returns empty when the only grant is a case mismatch (the CRITICAL 1 bug)', () => {
    const matches = checkPermission('io.github.Jarroslav/agentic-os', [
      { action: 'publish', resource: 'io.github.jarroslav/*' },
    ]);
    expect(matches).toEqual([]);
  });

  it('ignores permissions for a different action (e.g. edit)', () => {
    const matches = checkPermission('io.github.Jarroslav/agentic-os', [
      { action: 'edit', resource: 'io.github.Jarroslav/*' },
    ]);
    expect(matches).toEqual([]);
  });

  it('returns empty for an empty permissions array', () => {
    expect(checkPermission('io.github.Jarroslav/agentic-os', [])).toEqual([]);
  });

  it('ignores malformed permission entries instead of throwing', () => {
    const matches = checkPermission('io.github.Jarroslav/agentic-os', [
      null,
      { action: 'publish' }, // no resource field
      { action: 'publish', resource: 'io.github.Jarroslav/*' },
    ] as unknown as Array<{ action: string; resource: string }>);
    expect(matches).toHaveLength(1);
  });
});
