import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'vastu-pipeline-test-'));
const compiled = ts.transpileModule(fs.readFileSync(new URL('../../src/components/pipeline/pipelineState.ts', import.meta.url), 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
}).outputText;
const target = path.join(temporary, 'pipelineState.mjs');
fs.writeFileSync(target, compiled);
after(() => fs.rmSync(temporary, { recursive: true, force: true }));
const { pipelineState, currentStages, terminalPipeline, isSubmitted } = await import(pathToFileURL(target));
const base = () => ({ session: { id: 'sess_test', status: 'UPLOADING', job_id: 'job-current' }, stages: [], job: { id: 'job-current', stage: 'preprocessing' } });
const stage = (name, status, date, job = 'job-current') => ({ stage_name: name, status, updated_at: date, job_id: job });

test('a worker failure overrides a session still marked uploading', () => {
  const scan = base(); scan.job.stage = 'failed';
  assert.equal(pipelineState(scan).tone, 'failed');
  assert.equal(terminalPipeline(scan), true);
});
test('the most recent executing stage is used even when stage numbers run out of order', () => {
  const scan = base();
  scan.stages = [stage('RECONSTRUCTION_04', 'RUNNING', '2026-11-01T10:00:00Z'), stage('RECONSTRUCTION_03', 'RUNNING', '2026-11-01T10:01:00Z')];
  assert.equal(pipelineState(scan).stage.stage_name, 'RECONSTRUCTION_03');
});
test('failed events from a previous processing attempt do not label a new attempt as failed', () => {
  const scan = base(); scan.job.stage = 'queued';
  scan.stages = [stage('COMPLETED', 'FAILED', '2026-11-01T10:00:00Z', 'previous-job')];
  assert.equal(currentStages(scan).length, 0);
  assert.equal(pipelineState(scan).tone, 'queued');
});
test('viewer ready requires a published URL and successful job and session', () => {
  const scan = base(); scan.session.status = 'COMPLETED'; scan.job.stage = 'completed';
  assert.notEqual(pipelineState(scan).tone, 'complete');
  scan.session.viewer_url = '/uploads/scratch/job/result/index.html';
  assert.equal(pipelineState(scan).tone, 'complete');
});
test('automatic retry remains active rather than becoming a terminal failure', () => {
  const scan = base(); scan.stages = [stage('RECONSTRUCTION_00', 'RETRYING', '2026-11-01T10:00:00Z')];
  assert.equal(pipelineState(scan).tone, 'retrying');
  assert.equal(terminalPipeline(scan), false);
});
test('a scan appears on the project as soon as its upload is initialized', () => {
  assert.equal(isSubmitted({ status: 'AUTHORIZED' }), false);
  assert.equal(isSubmitted({ upload_id: 'upload-id' }), true);
});
