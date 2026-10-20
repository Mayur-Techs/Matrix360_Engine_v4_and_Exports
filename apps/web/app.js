const state = { files: [], datasets: [], jobs: [], selectedDataset: null, selectedJob: null, page: 'dashboard', advancedFilters: [], filterMetadata: null, filterMetadataJob: null, schemaCatalog: null, schemaSuggestions: [], processMode: 'verified', audiencePlan: null, pipelinePlan: null, pipelineAudiencePlan: null, pipelinePreview: null, profiles: [], jobStatuses: {} };
const districts = ['Alipurduar','Bankura','Birbhum','Cooch Behar','Dakshin Dinajpur','Darjeeling','Hooghly','Howrah','Jalpaiguri','Jhargram','Kalimpong','Kolkata','Malda','Murshidabad','Nadia','North 24 Parganas','Paschim Bardhaman','Paschim Medinipur','Purba Bardhaman','Purba Medinipur','Purulia','South 24 Parganas','Uttar Dinajpur'];
const $ = (id) => document.getElementById(id);
const api = async (path, options = {}) => {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  const payload = response.headers.get('content-type')?.includes('application/json') ? await response.json() : null;
  if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status})`);
  return payload;
};
const toast = (message) => { const node = $('toast'); node.textContent = message; node.classList.add('show'); setTimeout(() => node.classList.remove('show'), 3500); };
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const selected = (id) => [...$(id).selectedOptions].map(option => option.value || option.textContent);

function workflowStep(page) {
  if (page === 'upload') return 1;
  if (page === 'processing') return 2;
  if (['jobs', 'results', 'exports'].includes(page)) return 3;
  return 0;
}
function updateWorkflowRail() {
  const currentStep = workflowStep(state.page);
  document.querySelectorAll('[data-workflow-page]').forEach(button => {
    const step = Number(button.dataset.workflowStep);
    button.classList.toggle('active', step === currentStep);
    button.classList.toggle('complete', step < currentStep || (step === 1 && Boolean(state.selectedDataset)) || (step === 3 && Boolean(state.selectedJob)));
  });
}
function switchPage(page, focus = false) {
  state.page = page;
  document.querySelectorAll('[data-page]').forEach(section => { section.hidden = section.dataset.page !== page; });
  document.querySelectorAll('[data-page-link]').forEach(link => link.classList.toggle('active', link.dataset.pageLink === page));
  updateWorkflowRail();
  if (page === 'jobs') renderJobLog();
  if ((page === 'results' || page === 'exports') && state.selectedJob) selectJob(state.selectedJob);
  if (focus) requestAnimationFrame(() => document.querySelector(`[data-page="${page}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
}

function setFiles(files) {
  state.files = [...files]; $('upload').disabled = !state.files.length;
  $('file-tree').className = 'file-tree';
  $('file-tree').innerHTML = state.files.length ? state.files.map(f => `<div><strong>${escapeHtml(f.webkitRelativePath || f.name)}</strong><span>${(f.size / 1024).toFixed(1)} KB</span></div>`).join('') : 'No files selected.';
}
function renderSchemaCatalog(catalog, suggestions = []) {
  state.schemaCatalog = catalog; state.schemaSuggestions = suggestions;
  const suggestionByHeader = new Map(suggestions.map(item => [item.header, item]));
  $('schema-catalog').hidden = false;
  $('schema-summary').innerHTML = [
    ['Fixed constants', catalog.summary.fixed_fields, 'Contact and location fields retained'],
    ['Filter candidates', catalog.summary.filter_fields, 'Observed business attributes'],
    ['AI-safe headers', catalog.summary.ai_eligible_fields, 'Headers only, no record values'],
  ].map(([label, value, note]) => `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span><small>${escapeHtml(note)}</small></div>`).join('');
  $('schema-fields').innerHTML = catalog.fields.length ? catalog.fields.map(field => {
    const suggestion = suggestionByHeader.get(field.header);
    const group = suggestion?.group || field.group;
    const label = suggestion?.label || field.label;
    return `<article class="schema-field ${field.fixed ? 'fixed' : ''}"><span class="schema-field-group">${escapeHtml(group)}</span><strong>${escapeHtml(label)}</strong><small>${field.fixed ? 'Preserved constant' : `${escapeHtml(field.kind)} filter candidate`}</small>${suggestion ? `<em>AI: ${escapeHtml(suggestion.reason)}</em>` : ''}</article>`;
  }).join('') : '<p class="empty">No usable headers were found in this dataset.</p>';
  const inspection = catalog.inspection || { status: 'ready', message: '' };
  $('schema-catalog-copy').textContent = inspection.status === 'ready'
    ? 'Core identity and location fields are preserved. The remaining observed columns become filter candidates.'
    : inspection.message;
  $('schema-ai-notice').textContent = [inspection.message, catalog.ai.transfer_scope].filter(Boolean).join(' ');
  $('improve-schema').hidden = !catalog.ai.available || !catalog.summary.ai_eligible_fields;
}
async function loadSchemaCatalog(datasetId) {
  const catalog = await api(`/api/v1/datasets/${datasetId}/schema-catalog`);
  renderSchemaCatalog(catalog);
}
function datasetRadio() {
  $('dataset-picker').innerHTML = state.datasets.length ? state.datasets.map(d => `<label class="dataset"><input type="radio" name="dataset" value="${d.id}" ${state.selectedDataset === d.id ? 'checked' : ''}/><span><strong>${d.files.length} file${d.files.length === 1 ? '' : 's'}</strong><small>${d.files.map(f => escapeHtml(f.relative_path)).join(', ')}</small></span></label>`).join('') : 'Upload a dataset to begin.';
  $('start-job').disabled = !state.selectedDataset; $('suggest-audience-plan').disabled = !state.selectedDataset; $('suggest-pipeline-plan').disabled = !state.selectedDataset; $('preview-pipeline-plan').disabled = !state.pipelinePlan;
  document.querySelectorAll('input[name=dataset]').forEach(input => input.addEventListener('change', async e => { state.selectedDataset = e.target.value; state.audiencePlan = null; state.pipelinePlan = null; state.pipelineAudiencePlan = null; state.pipelinePreview = null; renderPipelinePlanEditor(); $('start-job').disabled = false; $('suggest-audience-plan').disabled = false; $('suggest-pipeline-plan').disabled = false; $('preview-pipeline-plan').disabled = true; $('start-ai-job').disabled = true; $('audience-plan').textContent = 'Describe the segment, then review its safe filter plan before it can run.'; $('pipeline-plan-status').textContent = 'Describe the segment, then review and validate the schema-bound filter plan.'; try { await loadSchemaCatalog(state.selectedDataset); } catch (error) { toast(error.message); } }));
}
function setProcessMode(mode) { state.processMode = mode; $('verified-mode').hidden = mode !== 'verified'; $('ai-direct-mode').hidden = mode !== 'ai-direct'; document.querySelectorAll('[data-process-mode]').forEach(button => button.classList.toggle('selected', button.dataset.processMode === mode)); }
function renderAudiencePlan(plan) { const predicate = plan.predicate ? JSON.stringify(plan.predicate) : 'No executable predicate'; const explanation = plan.segment_explanation?.length ? plan.segment_explanation.join(' ') : 'No supported condition was inferred.'; const unknown = plan.unknown_conditions?.length ? `<br/><small>Needs attention: ${escapeHtml(plan.unknown_conditions.join(' '))}</small>` : ''; const context = plan.provider?.context_scope ? ` · ${plan.provider.context_scope.replaceAll('+', ' + ')}` : ''; $('audience-plan').innerHTML = `<strong>Review required · ${escapeHtml(plan.provider.name)}${escapeHtml(context)}</strong><br/>${escapeHtml(explanation)}<br/><code>${escapeHtml(predicate)}</code>${unknown}<br/><small>${escapeHtml(plan.warnings[0])}</small>`; }

const TEXT_FILTER_OPERATORS = [['contains', 'contains'], ['excludes', 'does not contain'], ['eq', 'equals'], ['neq', 'does not equal'], ['present', 'is present'], ['empty', 'is empty']];
const NUMERIC_FILTER_OPERATORS = [['gt', 'greater than'], ['gte', 'greater than or equal to'], ['lt', 'less than'], ['lte', 'less than or equal to'], ['between', 'between (inclusive)']];

function pipelineFields() { return state.schemaCatalog?.fields || []; }
function pipelineField(field) { return pipelineFields().find(item => item.header === field); }
function defaultPipelineLeaf() {
  const candidate = pipelineFields().find(item => !item.fixed) || pipelineFields()[0];
  return { field: candidate?.header || '', operator: 'contains', value: '' };
}
function planNode(path) {
  let node = state.pipelinePlan;
  if (!path) return node;
  for (const index of path.split('.').map(Number)) node = node?.children?.[index];
  return node;
}
function planParent(path) {
  const parts = path.split('.'); const index = Number(parts.pop());
  return { parent: planNode(parts.join('.')), index };
}
function markPipelinePlanDirty() {
  state.pipelinePreview = null; state.pipelineAudiencePlan = null;
  $('pipeline-plan-status').textContent = 'Plan edited. Validate and preview the complete plan before approval.';
}
function pipelineOperatorOptions(field, selectedOperator) {
  const numeric = Boolean(pipelineField(field)?.numeric_eligible);
  const options = [...TEXT_FILTER_OPERATORS, ...(numeric ? NUMERIC_FILTER_OPERATORS : [])];
  return options.map(([value, label]) => `<option value="${value}" ${value === selectedOperator ? 'selected' : ''}>${label}</option>`).join('');
}
function renderPipelineLeaf(node, path) {
  const value = Array.isArray(node.value) ? node.value.join(', ') : (node.value ?? '');
  const hideValue = node.operator === 'present' || node.operator === 'empty';
  const fieldOptions = pipelineFields().map(field => `<option value="${escapeHtml(field.header)}" ${field.header === node.field ? 'selected' : ''}>${escapeHtml(field.label)}${field.numeric_eligible ? ' · numeric' : ''}</option>`).join('');
  return `<div class="filter-plan-leaf" data-plan-path="${path}"><label>Field<select data-plan-field="${path}"><option value="">Choose field</option>${fieldOptions}</select></label><label>Rule<select data-plan-operator="${path}">${pipelineOperatorOptions(node.field, node.operator)}</select></label><label ${hideValue ? 'hidden' : ''} data-plan-value-label="${path}">Value<input data-plan-value="${path}" value="${escapeHtml(value)}" placeholder="${node.operator === 'between' ? 'lower, upper' : 'value'}" /></label><button type="button" class="quiet" data-plan-remove="${path}">Remove</button></div>`;
}
function renderPipelineNode(node, path = '', depth = 0) {
  if (!node?.op) return renderPipelineLeaf(node || defaultPipelineLeaf(), path);
  const canAdd = node.op !== 'not';
  const children = node.children || [];
  return `<fieldset class="filter-plan-group depth-${depth}"><legend>(${node.op.toUpperCase()} group)</legend><label>Join<select data-plan-group="${path}"><option value="all" ${node.op === 'all' ? 'selected' : ''}>ALL / AND</option><option value="any" ${node.op === 'any' ? 'selected' : ''}>ANY / OR</option><option value="not" ${node.op === 'not' ? 'selected' : ''}>NOT</option></select></label><div class="filter-plan-children">${children.map((child, index) => renderPipelineNode(child, path ? `${path}.${index}` : String(index), depth + 1)).join('')}</div><div class="filter-plan-actions">${canAdd ? `<button type="button" class="secondary" data-plan-add-leaf="${path}">Add condition</button><button type="button" class="secondary" data-plan-add-group="${path}" ${depth >= 3 ? 'disabled' : ''}>Add nested group</button>` : '<small>NOT contains exactly one condition or group.</small>'}${path ? `<button type="button" class="quiet" data-plan-remove="${path}">Remove group</button>` : ''}</div></fieldset>`;
}
function renderPipelinePlanEditor() {
  const editor = $('pipeline-plan-editor');
  if (!state.pipelinePlan) { editor.hidden = true; editor.innerHTML = ''; return; }
  editor.hidden = false; editor.innerHTML = `<p class="eyebrow">EDITABLE LOGICAL FILTER PLAN</p><p>Parentheses are explicit. Numeric rules appear only for fields verified as quantitative during inspection.</p>${renderPipelineNode(state.pipelinePlan)}<p class="notice">Missing comparisons do not match. BETWEEN includes both boundaries. Identifier fields such as phone, PIN and GST never receive numeric comparison rules.</p>`;
}
function updatePipelineLeaf(path, key, value) {
  const node = planNode(path); if (!node || node.op) return;
  if (key === 'operator') {
    node.operator = value;
    if (value === 'present' || value === 'empty') node.value = null;
    else if (node.value == null) node.value = '';
  } else if (key === 'value') node.value = node.operator === 'between' ? value.split(',').map(item => item.trim()).filter(Boolean) : value;
  else node[key] = value;
  markPipelinePlanDirty(); renderPipelinePlanEditor();
}
function removePipelineNode(path) {
  const { parent, index } = planParent(path);
  if (!parent?.children || parent.op === 'not') return;
  parent.children.splice(index, 1);
  markPipelinePlanDirty(); renderPipelinePlanEditor();
}
function attachPipelineEditor() {
  const editor = $('pipeline-plan-editor');
  editor.addEventListener('change', event => {
    const target = event.target;
    if (target.matches('[data-plan-field]')) updatePipelineLeaf(target.dataset.planField, 'field', target.value);
    if (target.matches('[data-plan-operator]')) updatePipelineLeaf(target.dataset.planOperator, 'operator', target.value);
    if (target.matches('[data-plan-value]')) updatePipelineLeaf(target.dataset.planValue, 'value', target.value);
    if (target.matches('[data-plan-group]')) {
      const node = planNode(target.dataset.planGroup);
      if (target.value === 'not' && node.children.length !== 1) { target.value = node.op; toast('NOT requires exactly one child. Add it as a nested group instead.'); return; }
      node.op = target.value; markPipelinePlanDirty(); renderPipelinePlanEditor();
    }
  });
  editor.addEventListener('click', event => {
    const button = event.target.closest('button'); if (!button) return;
    if (button.dataset.planAddLeaf !== undefined) { const node = planNode(button.dataset.planAddLeaf); node.children.push(defaultPipelineLeaf()); markPipelinePlanDirty(); renderPipelinePlanEditor(); }
    if (button.dataset.planAddGroup !== undefined) { const node = planNode(button.dataset.planAddGroup); node.children.push({ op: 'all', children: [defaultPipelineLeaf()] }); markPipelinePlanDirty(); renderPipelinePlanEditor(); }
    if (button.dataset.planRemove !== undefined) removePipelineNode(button.dataset.planRemove);
  });
}
function renderProfiles() {
  const direct = $('ai-direct-profile'); if (!direct) return;
  const options = state.profiles.map(profile => `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.name)} · v${escapeHtml(profile.version)}</option>`).join('');
  direct.innerHTML = `<option value="">No profile context</option>${options}`;
  const process = $('process-profile-filter');
  const selectedProfiles = new Set(selected('process-profile-filter'));
  process.innerHTML = state.profiles.map(profile => `<option value="${escapeHtml(profile.id)}" ${selectedProfiles.has(profile.id) || ['lakhotia','shree','vrindavan'].includes(profile.id) ? 'selected' : ''}>${escapeHtml(profile.name)} · v${escapeHtml(profile.version)}</option>`).join('');
}
async function loadProfiles() {
  const result = await api('/api/v1/client-profiles'); state.profiles = result.profiles || []; renderProfiles();
}
function filterLabel(field) {
  const known = state.filterMetadata?.fields?.find(item => item.id === field);
  return known?.label || field;
}
function renderAdvancedFilters() {
  const output = $('active-advanced-filters');
  if (!state.advancedFilters.length) {
    output.className = 'filter-chips empty'; output.textContent = 'No additional filters applied.'; return;
  }
  output.className = 'filter-chips';
  output.innerHTML = state.advancedFilters.map((filter, index) => `<span class="filter-chip">${escapeHtml(filterLabel(filter.field))} ${escapeHtml(filter.operator.replaceAll('_', ' '))}${filter.values.length ? `: ${escapeHtml(filter.values.join(', '))}` : ''}<button type="button" data-remove-filter="${index}" aria-label="Remove filter">×</button></span>`).join('');
  document.querySelectorAll('[data-remove-filter]').forEach(button => button.addEventListener('click', () => { state.advancedFilters.splice(Number(button.dataset.removeFilter), 1); renderAdvancedFilters(); state.selectedJob && selectJob(state.selectedJob); }));
}
function renderFilterBuilder(metadata) {
  const field = $('advanced-filter-field');
  const available = metadata.fields.filter(item => item.available_records > 0);
  const groups = new Map();
  available.forEach(item => groups.set(item.group, [...(groups.get(item.group) || []), item]));
  const standard = [...groups].map(([group, fields]) => `<optgroup label="${escapeHtml(group)}">${fields.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)} · ${item.available_records.toLocaleString()} records</option>`).join('')}</optgroup>`).join('');
  const imported = metadata.imported_fields.filter(header => !available.some(item => item.id.toLowerCase() === header.toLowerCase()));
  field.innerHTML = `<option value="">Choose a field</option>${standard}${imported.length ? `<optgroup label="Imported source columns">${imported.map(header => `<option value="${escapeHtml(header)}">${escapeHtml(header)} · imported column</option>`).join('')}</optgroup>` : ''}`;
  ['advanced-filter-field','advanced-filter-operator','advanced-filter-value','add-advanced-filter'].forEach(id => { $(id).disabled = false; });
  const profiled = metadata.imported_field_profiles || [];
  $('filter-hint').textContent = `${available.length} normalized fields and ${imported.length} imported columns are available. ${metadata.profiling_scope || ''}`;
  $('vehicle-filter-notice').hidden = !available.some(item => item.group === 'Vehicle (observed data only)');
  $('vehicle-filter-notice').textContent = metadata.vehicle_notice;
  renderAdvancedFilters();
}
function updateAdvancedFilterChoices() {
  const field = $('advanced-filter-field').value;
  const profile = state.filterMetadata?.imported_field_profiles?.find(item => item.header === field);
  $('advanced-filter-values').innerHTML = (profile?.values || []).map(item => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.value)} · ${Number(item.records).toLocaleString()} records</option>`).join('');
}
function jobsTable() {
  $('jobs').innerHTML = state.jobs.length ? `<div class="job-list">${state.jobs.map(j => {
    const percent = Number.isFinite(j.progress_percent) ? j.progress_percent : 0;
    const detail = j.status === 'failed' ? `${j.error_code || 'Processing error'}${j.error_detail ? ` · ${j.error_detail}` : ''}` : `${j.progress_phase || j.status} · ${percent}%`;
    return `<button class="job ${j.id === state.selectedJob ? 'selected' : ''}" data-job="${j.id}"><span><strong>${j.status.replace('_', ' ')}</strong><small>${escapeHtml(j.dataset_name || j.dataset_id)}</small><small>${escapeHtml(detail)}</small><i class="job-progress"><i style="width:${Math.max(0, Math.min(100, percent))}%"></i></i><small>${new Date(j.created_at).toLocaleString()}</small></span><span>${j.report?.active_rows ?? '—'} rows</span></button>`;
  }).join('')}</div>` : 'No jobs yet.';
  document.querySelectorAll('[data-job]').forEach(button => button.addEventListener('click', () => selectJob(button.dataset.job)));
  $('active-count').textContent = state.jobs.filter(j => ['queued','running'].includes(j.status)).length;
  $('completed-count').textContent = state.jobs.filter(j => ['completed','needs_review'].includes(j.status)).length;
  $('review-count').textContent = state.jobs.filter(j => j.status === 'needs_review').length;
}
function renderJobLog() {
  const job = state.jobs.find(item => item.id === state.selectedJob);
  const download = $('download-job-log');
  if (!job) {
    $('job-log').className = 'job-log empty';
    $('job-log').textContent = 'Select a job to see its processing log.';
    download.hidden = true;
    return;
  }
  const reconciliation = job.report?.reconciliation || {};
  const exportCounts = job.report?.export_counts || {};
  const detail = job.error_detail || (job.status === 'failed' ? job.error_code || 'Processing failed.' : 'No error reported.');
  $('job-log').className = 'job-log';
  $('job-log').innerHTML = `<div><strong>${escapeHtml(job.status.replaceAll('_', ' '))}</strong><span>${escapeHtml(job.progress_phase || 'queued')} · ${job.progress_percent ?? 0}%</span></div><dl><div><dt>Dataset</dt><dd>${escapeHtml(job.dataset_name || job.report?.dataset_name || job.dataset_id)}</dd></div><div><dt>Rows processed</dt><dd>${escapeHtml(job.report?.active_rows ?? 'Pending')}</dd></div><div><dt>Input / filtered / export candidates</dt><dd>${escapeHtml(reconciliation.input_rows_processed ?? '—')} / ${escapeHtml(reconciliation.active_rows ?? '—')} / ${escapeHtml(exportCounts.Unique_export_candidates ?? '—')}</dd></div><div><dt>Duplicate review groups</dt><dd>${escapeHtml(reconciliation.deduplication_review_groups ?? '—')}</dd></div><div><dt>Message</dt><dd>${escapeHtml(detail)}</dd></div></dl>`;
  download.href = `/api/v1/jobs/${job.id}/log/download`;
  download.hidden = false;
}
async function loadWorkspace() {
  const previousStatuses = state.jobStatuses;
  const [datasets, jobs, audit] = await Promise.all([api('/api/v1/datasets'), api('/api/v1/jobs'), api('/api/v1/audit')]);
  state.datasets = datasets.datasets; state.jobs = jobs.jobs; $('dataset-count').textContent = state.datasets.length; datasetRadio(); jobsTable(); renderJobLog();
  state.jobStatuses = Object.fromEntries(state.jobs.map(job => [job.id, job.status]));
  $('audit-list').innerHTML = audit.events.length ? audit.events.map(e => `<div class="audit"><strong>${escapeHtml(e.action)}</strong><span>${escapeHtml(e.actor)} · ${new Date(e.created_at).toLocaleString()}</span></div>`).join('') : 'No activity yet.';
  const selectedJob = state.jobs.find(job => job.id === state.selectedJob);
  if (state.page === 'jobs' && selectedJob && previousStatuses[selectedJob.id] && previousStatuses[selectedJob.id] !== selectedJob.status && ['completed', 'needs_review'].includes(selectedJob.status)) {
    switchPage('results', true);
    toast('Processing finished. Review the audience and download-ready exports.');
  }
}
async function selectJob(jobId) {
  if (state.selectedJob && state.selectedJob !== jobId) { state.advancedFilters = []; state.filterMetadata = null; state.filterMetadataJob = null; }
  state.selectedJob = jobId; jobsTable(); renderJobLog();
  const filter = new URLSearchParams({limit:'50', search:$('search').value});
  selected('geo-filter').forEach(value => filter.append('geo_statuses', value));
  selected('district-filter').forEach(value => filter.append('districts', value));
  selected('profile-filter').forEach(value => filter.append('client_profiles', value));
  if (state.advancedFilters.length) filter.set('advanced_filters', JSON.stringify(state.advancedFilters));
  const [result, exports, metadata] = await Promise.all([api(`/api/v1/jobs/${jobId}/results?${filter}`), api(`/api/v1/jobs/${jobId}/exports`), state.filterMetadataJob === jobId ? Promise.resolve(state.filterMetadata) : api(`/api/v1/jobs/${jobId}/filter-metadata`)]);
  if (state.filterMetadataJob !== jobId) { state.filterMetadata = metadata; state.filterMetadataJob = jobId; renderFilterBuilder(metadata); }
  $('result-meta').textContent = `${result.total} matching records · ${result.status}`;
  // Show the retained source telephone string. The normalized value remains
  // available in exports for contact validation and duplicate review, but must not
  // replace source evidence in the director's review grid.
  const columns = ['name','company','phone_source','city','state','geo_status','lakhotia_class','shree_class','vrindavan_class'];
  $('result-head').innerHTML = `<tr>${columns.map(c => `<th>${c.replaceAll('_', ' ')}</th>`).join('')}</tr>`;
  $('result-body').innerHTML = result.rows.map(row => `<tr>${columns.map(c => `<td>${escapeHtml(row[c])}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${columns.length}">No records available.</td></tr>`;
  const profiles = exports.filters?.client_profiles?.join(', ') || 'No client profiles selected';
  const exportDistricts = exports.filters?.districts?.join(', ') || 'All West Bengal districts';
  const completed = exports.completed_at ? new Date(exports.completed_at).toLocaleString() : 'Processing not finished';
  const exportSummary = `<div class="notice"><strong>${escapeHtml(exports.dataset_name || 'Selected dataset')}</strong><br/>${escapeHtml(exports.status.replaceAll('_', ' '))} · ${escapeHtml(completed)}<br/><small>Client files: ${escapeHtml(profiles)} · Districts: ${escapeHtml(exportDistricts)}</small></div>`;
  $('export-list').innerHTML = exports.exports.length ? exportSummary + exports.exports.map(e => e.available
    ? `<a class="export" href="/api/v1/exports/${e.id}/download" download><strong>${escapeHtml(e.name)}</strong><span>${(e.size_bytes / 1024).toFixed(1)} KB · SHA-256 ${escapeHtml(e.sha256.slice(0, 12))}…</span></a>`
    : `<div class="export unavailable"><strong>${escapeHtml(e.name)}</strong><span>Unavailable in local storage. Re-run the job to generate a fresh export.</span></div>`).join('') : exportSummary + 'No exports available until the job completes.';
}
async function loggedIn() {
  const session = await api('/api/v1/auth/session');
  if (!session.authenticated) return false;
  const user = session.user; $('workspace').textContent = `${user.tenant_id} / ${user.role}`; $('login-panel').hidden = true; $('console').hidden = false; await Promise.all([loadWorkspace(), loadProfiles()]); return true;
}
$('login-form').addEventListener('submit', async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); try { const user = await api('/api/v1/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) }); $('workspace').textContent = `${user.tenant_id} / ${user.role}`; $('login-panel').hidden = true; $('console').hidden = false; await Promise.all([loadWorkspace(), loadProfiles()]); } catch (error) { $('login-error').textContent = error.message; } });
$('logout').addEventListener('click', async () => { await api('/api/v1/auth/logout', {method:'POST'}); location.reload(); });
$('choose-files').onclick = () => $('files').click(); $('choose-folder').onclick = () => $('folder').click(); $('files').onchange = e => setFiles(e.target.files); $('folder').onchange = e => setFiles(e.target.files);
$('dropzone').addEventListener('dragover', e => { e.preventDefault(); $('dropzone').classList.add('dragging'); }); $('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('dragging')); $('dropzone').addEventListener('drop', e => { e.preventDefault(); $('dropzone').classList.remove('dragging'); setFiles(e.dataTransfer.files); });
$('upload-form').addEventListener('submit', async event => { event.preventDefault(); if (!state.files.length) return; const form = new FormData(); state.files.forEach(file => form.append('files', file)); form.append('relative_paths', JSON.stringify(state.files.map(file => file.webkitRelativePath || file.name))); $('upload').disabled = true; try { const result = await api('/api/v1/datasets', {method:'POST', body:form}); state.selectedDataset = result.dataset_id; $('inspection').hidden = false; $('inspection').innerHTML = result.files.map(file => `<div><strong>${escapeHtml(file.name)}</strong><p>SHA-256 ${file.sha256.slice(0,16)}… · ${file.size_bytes} bytes</p><code>${escapeHtml(file.inspection.headers.length ? file.inspection.headers.join(' | ') : file.inspection.warning || 'No headers detected')}</code></div>`).join(''); await loadSchemaCatalog(result.dataset_id); await loadWorkspace(); switchPage('processing', true); $('pipeline-objective').focus(); toast('Upload complete. Describe the audience to create a reviewable processing plan.'); } catch (error) { toast(error.message); } finally { $('upload').disabled = false; } });
$('improve-schema').addEventListener('click', async () => { if (!state.selectedDataset || !state.schemaCatalog) return; const button = $('improve-schema'); button.disabled = true; button.textContent = 'Refining…'; try { const result = await api(`/api/v1/datasets/${state.selectedDataset}/schema-ai-suggestions`, {method:'POST'}); renderSchemaCatalog(state.schemaCatalog, result.suggestions); $('schema-ai-notice').textContent = result.transfer_scope; toast('AI label suggestions are ready for review.'); } catch (error) { toast(error.message); } finally { button.disabled = false; button.textContent = 'AI refine labels'; } });
document.querySelectorAll('[data-process-mode]').forEach(button => button.addEventListener('click', () => setProcessMode(button.dataset.processMode)));
$('ai-direct-profile').addEventListener('change', event => { const profile = state.profiles.find(item => item.id === event.target.value); const objective = profile?.default_objective || profile?.definition?.audience_objective; if (objective) $('ai-objective').value = objective; });
$('suggest-pipeline-plan').addEventListener('click', async () => { if (!state.selectedDataset) return; const objective = $('pipeline-objective').value.trim(); if (objective.length < 3) { toast('Describe the audience segment first.'); return; } const button = $('suggest-pipeline-plan'); button.disabled = true; try { const plan = await api(`/api/v1/datasets/${state.selectedDataset}/ai-assisted/plan`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({objective})}); const predicateIsGroup = Boolean(plan.predicate?.op); state.pipelinePlan = plan.predicate && !predicateIsGroup ? {op:'all', children:[plan.predicate]} : plan.predicate; state.pipelineAudiencePlan = predicateIsGroup ? plan : null; state.pipelinePreview = null; renderPipelinePlanEditor(); $('preview-pipeline-plan').disabled = !plan.predicate; $('pipeline-planner-status').textContent = plan.provider.name === 'openai-responses' ? `AI-assisted planner · ${plan.provider.context_scope}. No source rows or contacts were sent.` : 'Local deterministic fallback — the model was unavailable, so only explicit objective terms and observed headers were used.'; $('pipeline-plan-status').textContent = plan.predicate ? 'Proposed plan ready. Edit it if needed, then validate and preview before approval.' : `No broad audience was created. ${plan.unknown_conditions.join(' ')}`; toast(plan.predicate ? 'Schema-bound AI-assisted plan ready for review.' : 'No executable plan was inferred.'); } catch (error) { toast(error.message); } finally { button.disabled = false; } });
$('preview-pipeline-plan').addEventListener('click', async () => { if (!state.selectedDataset || !state.pipelinePlan) return; const button = $('preview-pipeline-plan'); button.disabled = true; try { const preview = await api(`/api/v1/datasets/${state.selectedDataset}/filter-plans/preview`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({plan:state.pipelinePlan})}); state.pipelinePlan = preview.plan; state.pipelinePreview = preview; renderPipelinePlanEditor(); $('pipeline-plan-status').textContent = `${preview.matched_rows.toLocaleString()} matching row(s) in the bounded preview of ${preview.checked_rows.toLocaleString()} CSV/TSV row(s)${preview.truncated ? ' (truncated)' : ''}. Approval will run the authoritative V4 worker.`; toast('Plan validated and previewed.'); } catch (error) { state.pipelinePreview = null; toast(error.message); } finally { button.disabled = false; } });
$('suggest-audience-plan').addEventListener('click', async () => { if (!state.selectedDataset) return; const objective = $('ai-objective').value.trim(); if (objective.length < 3) { toast('Describe the audience segment first.'); return; } const button = $('suggest-audience-plan'); button.disabled = true; try { const plan = await api(`/api/v1/datasets/${state.selectedDataset}/ai-direct/plan`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({objective, profile_id:$('ai-direct-profile').value || null})}); state.audiencePlan = plan; renderAudiencePlan(plan); $('start-ai-job').disabled = !plan.predicate; toast(plan.predicate ? 'Plan ready for your approval.' : 'The request needs a supported source field.'); } catch (error) { toast(error.message); } finally { button.disabled = false; } });
$('start-ai-job').addEventListener('click', async () => { if (!state.selectedDataset || !state.audiencePlan?.predicate) return; const clientProfiles = selected('process-profile-filter'); if (!clientProfiles.length) { toast('Choose at least one client export file.'); return; } const button = $('start-ai-job'); button.disabled = true; try { const job = await api('/api/v1/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dataset_id: state.selectedDataset, idempotency_key: crypto.randomUUID(), client_profiles: clientProfiles, districts: selected('process-district-filter'), filter_plan: state.audiencePlan.predicate, audience_plan: state.audiencePlan})}); state.selectedJob = job.job_id; await loadWorkspace(); switchPage('jobs'); toast(`AI Direct plan approved. Job ${job.job_id.slice(0,8)} is queued.`); } catch (error) { toast(error.message); button.disabled = false; } });
function updateAdvancedFilterValueInput() {
  const noValue = ['is_present','is_empty'].includes($('advanced-filter-operator').value);
  $('advanced-filter-value-label').hidden = noValue;
  $('advanced-filter-value').disabled = noValue;
}
$('advanced-filter-operator').addEventListener('change', updateAdvancedFilterValueInput);
$('advanced-filter-field').addEventListener('change', updateAdvancedFilterChoices);
$('add-advanced-filter').addEventListener('click', () => {
  const field = $('advanced-filter-field').value;
  const operator = $('advanced-filter-operator').value;
  const values = $('advanced-filter-value').value.split(',').map(value => value.trim()).filter(Boolean);
  if (!field) { toast('Choose a field to filter.'); return; }
  if (!['is_present','is_empty'].includes(operator) && !values.length) { toast('Enter one or more comma-separated values.'); return; }
  state.advancedFilters.push({field, operator, values});
  $('advanced-filter-value').value = ''; renderAdvancedFilters(); state.selectedJob && selectJob(state.selectedJob);
});
$('start-job').addEventListener('click', async () => { if (!state.selectedDataset) return; const clientProfiles = selected('process-profile-filter'); if (!clientProfiles.length) { toast('Choose at least one client export file.'); return; } if (state.pipelinePlan && !state.pipelinePreview) { toast('Validate and preview the edited filter plan before approval.'); return; } $('start-job').disabled = true; try { if (state.pipelinePlan) await api(`/api/v1/datasets/${state.selectedDataset}/filter-plans/apply`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({plan:state.pipelinePlan})}); const payload = {dataset_id: state.selectedDataset, idempotency_key: crypto.randomUUID(), client_profiles: clientProfiles, districts: selected('process-district-filter'), ai_review_enabled: $('ai-review-enabled').checked}; if (state.pipelinePlan) payload.filter_plan = state.pipelinePlan; if (state.pipelineAudiencePlan) payload.audience_plan = state.pipelineAudiencePlan; const job = await api('/api/v1/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); state.selectedJob = job.job_id; await loadWorkspace(); switchPage('jobs'); toast(`Approved job queued: ${job.job_id.slice(0,8)}. Follow its live processing log here.`); } catch (error) { toast(error.message); $('start-job').disabled = false; } });
const districtOptions = districts.map(district => `<option value="${escapeHtml(district)}">${escapeHtml(district)}</option>`).join('');
$('district-filter').innerHTML = districtOptions; $('process-district-filter').innerHTML = districtOptions;
document.querySelectorAll('.refresh').forEach(button => button.onclick = loadWorkspace); $('new-job').onclick = () => switchPage('upload', true); $('run-search').onclick = () => state.selectedJob && selectJob(state.selectedJob);
document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); switchPage(link.dataset.pageLink); }));
document.querySelectorAll('[data-workflow-page]').forEach(button => button.addEventListener('click', () => switchPage(button.dataset.workflowPage, true)));
attachPipelineEditor();
loggedIn().then(() => switchPage(state.page)); setInterval(() => !document.hidden && $('console').hidden === false && loadWorkspace().catch(() => {}), 8000);

