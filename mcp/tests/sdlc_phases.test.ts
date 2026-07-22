import { describe, expect, it } from 'vitest';
import { parsePhaseMap } from '../src/tools/list_sdlc_phases.js';

describe('parsePhaseMap', () => {
  it('parses a normal small table', () => {
    const md = `
## Phase map

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | Doctor | no | — |
| 1 | Requirements | no | \`requirements.ambiguous\` |
| 2 | Plan | no | \`plan.approved\` |
`;
    const phases = parsePhaseMap(md);
    expect(phases).toHaveLength(3);
    expect(phases.map(p => p.number)).toEqual([0, 1, 2]);
    expect(phases[1]?.name).toBe('Requirements');
    expect(phases[1]?.gates).toEqual(['requirements.ambiguous']);
  });

  it('ignores prose containing a pipe before the table', () => {
    const md = `
## Phase map

Phases run in order | see the table below.

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | Doctor | no | — |
| 1 | Requirements | no | \`requirements.ambiguous\` |
`;
    const phases = parsePhaseMap(md);
    expect(phases).toHaveLength(2);
    expect(phases.map(p => p.number)).toEqual([0, 1]);
  });

  it('does not absorb a second table immediately following with no blank-line separator', () => {
    const md = `
## Phase map

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | Doctor | no | — |
| 1 | Requirements | no | \`requirements.ambiguous\` |
| # | Other | Column | Header |
|---|---|---|---|
| 99 | Not a phase | no | \`bogus.gate\` |
`;
    const phases = parsePhaseMap(md);
    expect(phases.map(p => p.number)).toEqual([0, 1]);
    expect(phases.some(p => p.number === 99)).toBe(false);
  });

  it('returns [] for a renamed heading', () => {
    const md = `
## Phases

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | Doctor | no | — |
`;
    expect(parsePhaseMap(md)).toEqual([]);
  });

  it('excludes backticked non-gate prose from the gate column, keeping only real gates', () => {
    const md = `
## Phase map

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | QA Checklist | per \`phase_set\` | \`spec.approved\` and \`some_thing\` noted |
`;
    const phases = parsePhaseMap(md);
    expect(phases[0]?.gates).toEqual(['spec.approved']);
  });
});
