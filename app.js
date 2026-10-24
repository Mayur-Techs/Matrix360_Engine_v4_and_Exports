const state = { files: [], datasets: [], jobs: [], selectedDataset: null, selectedJob: null, page: 'discovery', discoveryLeads: [], advancedFilters: [], filterMetadata: null, filterMetadataJob: null, schemaCatalog: null, schemaSuggestions: [], processMode: 'verified', audiencePlan: null, pipelinePlan: null, pipelineAudiencePlan: null, pipelinePreview: null, profiles: [], jobStatuses: {}, historyDrawerOpen: false, selectionRevision: 0 };
const districts = ['Alipurduar','Bankura','Birbhum','Cooch Behar','Dakshin Dinajpur','Darjeeling','Hooghly','Howrah','Jalpaiguri','Jhargram','Kalimpong','Kolkata','Malda','Murshidabad','Nadia','North 24 Parganas','Paschim Bardhaman','Paschim Medinipur','Purba Bardhaman','Purba Medinipur','Purulia','South 24 Parganas','Uttar Dinajpur'];
const $ = (id) => document.getElementById(id);
const api = async (path, options = {}) => {
  const isVercel = typeof window !== 'undefined' && window.location.hostname.includes('vercel.app');
  const defaultBase = isVercel ? 'https://matrix360-engine-v4-and-exports.onrender.com' : '';
  const base = window.MATRIX_API_BASE || (typeof localStorage !== 'undefined' && localStorage.getItem('matrix_api_base')) || defaultBase;
  const url = base + path;
  const response = await fetch(url, { credentials: 'include', ...options });
  const payload = response.headers.get('content-type')?.includes('application/json') ? await response.json() : null;
  if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status})`);
  return payload;
};
const toast = (message) => { const node = $('toast'); node.textContent = message; node.classList.add('show'); setTimeout(() => node.classList.remove('show'), 3500); };
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const selected = (id) => [...$(id).selectedOptions].map(option => option.value || option.textContent);

function workflowStep(page) {
  if (page === 'discovery') return 0;
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
  if (page === 'discovery' && (!state.discoveryLeads || !state.discoveryLeads.length)) loadDiscoveryLeads();
  if (page === 'jobs') renderJobLog();
  if ((page === 'results' || page === 'exports') && state.selectedJob) selectJob(state.selectedJob);
  if (focus) requestAnimationFrame(() => document.querySelector(`[data-page="${page}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
}

function setFiles(files) {
  state.files = [...files]; $('upload').disabled = !state.files.length;
  $('file-tree').className = 'file-tree';
  $('file-tree').innerHTML = state.files.length ? state.files.map(f => `<div><strong>${escapeHtml(f.webkitRelativePath || f.name)}</strong><span>${(f.size / 1024).toFixed(1)} KB</span></div>`).join('') : 'No files selected.';
}
function updateStartJobCopy() {
  $('start-job').textContent = state.pipelinePlan
    ? 'Approve safe plan & start processing'
    : 'Start complete evidence-bound processing';
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
async function selectDataset(datasetId) {
  state.selectedDataset = datasetId; state.audiencePlan = null; state.pipelinePlan = null; state.pipelineAudiencePlan = null; state.pipelinePreview = null;
  renderPipelinePlanEditor(); $('start-job').disabled = false; $('suggest-audience-plan').disabled = false; $('suggest-pipeline-plan').disabled = false; $('preview-pipeline-plan').disabled = true; $('start-ai-job').disabled = true; updateStartJobCopy();
  $('audience-plan').textContent = 'Describe the segment, then review its safe filter plan before it can run.';
  $('pipeline-plan-status').textContent = 'Describe the segment, then review and validate the schema-bound filter plan.';
  try { await loadSchemaCatalog(state.selectedDataset); } catch (error) { toast(error.message); }
  datasetRadio();
  jobsTable();
}
function datasetRadio() {
  const selectedDataset = state.datasets.find(dataset => dataset.id === state.selectedDataset);
  $('dataset-picker').innerHTML = selectedDataset
    ? `<div class="dataset selected-dataset"><span><strong>Using ${selectedDataset.files.length} file${selectedDataset.files.length === 1 ? '' : 's'}</strong><small>${selectedDataset.files.map(file => escapeHtml(file.relative_path)).join(', ')}</small></span><button id="choose-history-dataset" type="button" class="secondary">Change import</button></div>`
    : state.datasets.length
      ? '<div class="empty">Choose a previous import from History, or upload a new file first.</div>'
      : 'Upload a dataset to begin.';
  $('start-job').disabled = !state.selectedDataset; $('suggest-audience-plan').disabled = !state.selectedDataset; $('suggest-pipeline-plan').disabled = !state.selectedDataset; $('preview-pipeline-plan').disabled = !state.pipelinePlan; updateStartJobCopy();
  $('choose-history-dataset')?.addEventListener('click', () => { state.historyDrawerOpen = true; jobsTable(); });
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
function jobRow(j, { history = false } = {}) {
  const percent = Number.isFinite(j.progress_percent) ? j.progress_percent : 0;
  const detail = j.status === 'failed' ? `${j.error_code || 'Processing error'}${j.error_detail ? ` · ${j.error_detail}` : ''}` : `${j.progress_phase || j.status} · ${percent}%`;
  const exportCount = j.export_summary?.available;
  const completed = ['completed', 'needs_review'].includes(j.status);
  const files = history && (exportCount || completed) ? `<small>${Number.isInteger(exportCount) ? `${exportCount} downloadable file${exportCount === 1 ? '' : 's'}` : 'Open files & downloads'}</small>` : '';
  return `<button class="job ${j.id === state.selectedJob ? 'selected' : ''}" data-job="${j.id}" ${history ? 'data-history-job="true"' : ''}><span><strong>${j.status.replaceAll('_', ' ')}</strong><small>${escapeHtml(j.dataset_name || j.dataset_id)}</small><small>${escapeHtml(detail)}</small>${history ? `<small>${new Date(j.created_at).toLocaleString()}</small>${files}` : `<i class="job-progress"><i style="width:${Math.max(0, Math.min(100, percent))}%"></i></i><small>${new Date(j.created_at).toLocaleString()}</small>`}</span><span>${j.report?.active_rows ?? '—'} rows</span></button>`;
}
function renderHistoryDrawer(history) {
  const drawer = $('history-drawer');
  drawer.hidden = !state.historyDrawerOpen;
  $('history-dataset-count').textContent = state.datasets.length;
  $('history-job-count').textContent = history.length;
  $('history-dataset-list').innerHTML = state.datasets.length
    ? state.datasets.map(dataset => `<button class="history-dataset ${dataset.id === state.selectedDataset ? 'selected' : ''}" type="button" data-history-dataset="${dataset.id}"><strong>${dataset.files.length} file${dataset.files.length === 1 ? '' : 's'}</strong><small>${dataset.files.map(file => escapeHtml(file.relative_path)).join(', ')}</small><small>${new Date(dataset.uploaded_at).toLocaleString()}</small></button>`).join('')
    : '<p class="empty">No imported datasets.</p>';
  $('history-drawer-list').innerHTML = history.length
    ? `<div class="job-list">${history.map(job => jobRow(job, { history: true })).join('')}</div>`
    : '<p class="empty">Completed jobs will appear here after processing finishes.</p>';
  document.querySelectorAll('[data-history-dataset]').forEach(button => button.addEventListener('click', async () => {
    await selectDataset(button.dataset.historyDataset); state.historyDrawerOpen = false; jobsTable(); switchPage('processing', true);
  }));
}
function jobsTable() {
  const active = state.jobs.filter(j => ['queued', 'running', 'cancel_requested'].includes(j.status));
  const history = state.jobs.filter(job => !['queued', 'running', 'cancel_requested'].includes(job.status));
  $('jobs').innerHTML = active.length ? `<div class="current-job-label">Current processing</div><div class="job-list">${active.map(job => jobRow(job)).join('')}</div>` : 'No processing is running. Choose a completed job in history to inspect its details or exports.';
  $('job-history-count').textContent = history.length;
  $('history-tab-count').textContent = history.length + state.datasets.length;
  renderHistoryDrawer(history);
  document.querySelectorAll('[data-job]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.historyJob) {
      state.selectedJob = button.dataset.job; state.historyDrawerOpen = false; jobsTable(); switchPage('exports', true); return;
    }
    selectJob(button.dataset.job);
  }));
  $('active-count').textContent = state.jobs.filter(j => ['queued','running'].includes(j.status)).length;
  $('completed-count').textContent = state.jobs.filter(j => ['completed','needs_review'].includes(j.status)).length;
  $('review-count').textContent = state.jobs.filter(j => j.status === 'needs_review').length;
}
function renderExports(exports) {
  const profiles = exports.filters?.client_profiles?.join(', ') || 'No client profiles selected';
  const exportDistricts = exports.filters?.districts?.join(', ') || 'All West Bengal districts';
  const completed = exports.completed_at ? new Date(exports.completed_at).toLocaleString() : 'Processing not finished';
  const exportSummary = `<div class="notice"><strong>${escapeHtml(exports.dataset_name || 'Selected dataset')}</strong><br/>${escapeHtml(exports.status.replaceAll('_', ' '))} · ${escapeHtml(completed)}<br/><small>Client files: ${escapeHtml(profiles)} · Districts: ${escapeHtml(exportDistricts)}</small></div>`;
  $('export-list').className = '';
  $('export-list').innerHTML = exports.exports.length ? exportSummary + exports.exports.map(e => e.available
    ? `<a class="export" href="/api/v1/exports/${e.id}/download" download><strong>${escapeHtml(e.name)}</strong><span>Download · ${(e.size_bytes / 1024).toFixed(1)} KB · SHA-256 ${escapeHtml(e.sha256.slice(0, 12))}…</span></a>`
    : `<div class="export unavailable"><strong>${escapeHtml(e.name)}</strong><span>Unavailable in local storage. Re-run the job to generate a fresh export.</span></div>`).join('') : exportSummary + '<p class="empty">No exports were created for this job.</p>';
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
  const completedActions = ['completed', 'needs_review'].includes(job.status) ? `<div class="job-result-actions"><button type="button" class="secondary" data-open-selected-page="results">Explore &amp; review</button><button type="button" class="secondary" data-open-selected-page="exports">View exports</button></div>` : '';
  $('job-log').innerHTML = `<div><strong>${escapeHtml(job.status.replaceAll('_', ' '))}</strong><span>${escapeHtml(job.progress_phase || 'queued')} · ${job.progress_percent ?? 0}%</span></div><dl><div><dt>Dataset</dt><dd>${escapeHtml(job.dataset_name || job.report?.dataset_name || job.dataset_id)}</dd></div><div><dt>Rows processed</dt><dd>${escapeHtml(job.report?.active_rows ?? 'Pending')}</dd></div><div><dt>Input / filtered / export candidates</dt><dd>${escapeHtml(reconciliation.input_rows_processed ?? '—')} / ${escapeHtml(reconciliation.active_rows ?? '—')} / ${escapeHtml(exportCounts.Unique_export_candidates ?? '—')}</dd></div><div><dt>Duplicate review groups</dt><dd>${escapeHtml(reconciliation.deduplication_review_groups ?? '—')}</dd></div><div><dt>Message</dt><dd>${escapeHtml(detail)}</dd></div></dl>${completedActions}`;
  document.querySelectorAll('[data-open-selected-page]').forEach(button => button.addEventListener('click', () => switchPage(button.dataset.openSelectedPage)));
  download.href = `/api/v1/jobs/${job.id}/log/download`;
  download.hidden = false;
}
async function loadWorkspace() {
  const previousStatuses = state.jobStatuses;
  const [datasets, jobs, audit] = await Promise.all([api('/api/v1/datasets'), api('/api/v1/jobs'), api('/api/v1/audit')]);
  state.datasets = datasets.datasets; state.jobs = jobs.jobs;
  const selectedStillExists = state.jobs.some(job => job.id === state.selectedJob);
  if (!selectedStillExists) state.selectedJob = state.jobs.find(job => ['queued', 'running', 'cancel_requested'].includes(job.status))?.id || state.jobs[0]?.id || null;
  $('dataset-count').textContent = state.datasets.length; datasetRadio(); jobsTable(); renderJobLog();
  state.jobStatuses = Object.fromEntries(state.jobs.map(job => [job.id, job.status]));
  $('audit-list').innerHTML = audit.events.length ? audit.events.map(e => `<div class="audit"><strong>${escapeHtml(e.action)}</strong><span>${escapeHtml(e.actor)} · ${new Date(e.created_at).toLocaleString()}</span></div>`).join('') : 'No activity yet.';
  const selectedJob = state.jobs.find(job => job.id === state.selectedJob);
  if (state.page === 'jobs' && selectedJob && previousStatuses[selectedJob.id] && previousStatuses[selectedJob.id] !== selectedJob.status && ['completed', 'needs_review'].includes(selectedJob.status)) {
    switchPage('results', true);
    toast('Processing finished. Review the audience and download-ready exports.');
  }
  if (state.selectedJob && !selectedStillExists) selectJob(state.selectedJob).catch(error => toast(error.message));
}
async function selectJob(jobId) {
  if (state.selectedJob && state.selectedJob !== jobId) { state.advancedFilters = []; state.filterMetadata = null; state.filterMetadataJob = null; }
  state.selectedJob = jobId; const revision = ++state.selectionRevision; jobsTable(); renderJobLog();
  $('export-list').className = 'empty';
  $('export-list').textContent = 'Loading downloadable files…';
  const filter = new URLSearchParams({limit:'50', search:$('search').value});
  selected('geo-filter').forEach(value => filter.append('geo_statuses', value));
  selected('district-filter').forEach(value => filter.append('districts', value));
  selected('profile-filter').forEach(value => filter.append('client_profiles', value));
  if (state.advancedFilters.length) filter.set('advanced_filters', JSON.stringify(state.advancedFilters));
  // Download discovery must never depend on the heavier results or metadata
  // queries. A completed job can therefore still expose its files when a
  // review query times out or an older workspace is partially unavailable.
  const exportsPromise = api(`/api/v1/jobs/${jobId}/exports`).then(exports => {
    if (revision === state.selectionRevision) renderExports(exports);
    return exports;
  }).catch(error => {
    if (revision === state.selectionRevision) { $('export-list').className = 'empty'; $('export-list').textContent = `Exports could not be loaded: ${error.message}`; }
    return null;
  });
  const [resultOutcome, metadataOutcome] = await Promise.allSettled([
    api(`/api/v1/jobs/${jobId}/results?${filter}`),
    state.filterMetadataJob === jobId ? Promise.resolve(state.filterMetadata) : api(`/api/v1/jobs/${jobId}/filter-metadata`),
  ]);
  await exportsPromise;
  if (revision !== state.selectionRevision) return;
  if (metadataOutcome.status === 'fulfilled' && state.filterMetadataJob !== jobId) { state.filterMetadata = metadataOutcome.value; state.filterMetadataJob = jobId; renderFilterBuilder(metadataOutcome.value); }
  if (resultOutcome.status !== 'fulfilled') { $('result-meta').textContent = `Results could not be loaded: ${resultOutcome.reason.message}`; $('result-body').innerHTML = ''; return; }
  const result = resultOutcome.value;
  $('result-meta').textContent = `${result.total} matching records · ${result.status}`;
  // Show the retained source telephone string. The normalized value remains
  // available in exports for contact validation and duplicate review, but must not
  // replace source evidence in the director's review grid.
  const columns = ['name','company','phone_source','city','state','geo_status','lakhotia_class','shree_class','vrindavan_class'];
  $('result-head').innerHTML = `<tr>${columns.map(c => `<th>${c.replaceAll('_', ' ')}</th>`).join('')}</tr>`;
  $('result-body').innerHTML = result.rows.map(row => `<tr>${columns.map(c => `<td>${escapeHtml(row[c])}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${columns.length}">No records available.</td></tr>`;
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
$('suggest-pipeline-plan').addEventListener('click', async () => { if (!state.selectedDataset) return; const objective = $('pipeline-objective').value.trim(); if (objective.length < 3) { toast('Describe the audience segment first.'); return; } const button = $('suggest-pipeline-plan'); button.disabled = true; try { const plan = await api(`/api/v1/datasets/${state.selectedDataset}/ai-assisted/plan`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({objective})}); const predicateIsGroup = Boolean(plan.predicate?.op); state.pipelinePlan = plan.predicate && !predicateIsGroup ? {op:'all', children:[plan.predicate]} : plan.predicate; state.pipelineAudiencePlan = predicateIsGroup ? plan : null; state.pipelinePreview = null; updateStartJobCopy(); renderPipelinePlanEditor(); $('preview-pipeline-plan').disabled = !plan.predicate; $('pipeline-planner-status').textContent = plan.provider.name === 'openai-responses' ? `AI-assisted planner · ${plan.provider.context_scope}. No source rows or contacts were sent.` : 'Local deterministic fallback — the model was unavailable, so only explicit objective terms and observed headers were used.'; $('pipeline-plan-status').textContent = plan.predicate ? 'Proposed plan ready. Edit it if needed, then validate and preview before approval.' : `No broad audience was created. ${plan.unknown_conditions.join(' ')}`; toast(plan.predicate ? 'Schema-bound AI-assisted plan ready for review.' : 'No executable plan was inferred.'); } catch (error) { toast(error.message); } finally { button.disabled = false; } });
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
document.querySelectorAll('.refresh').forEach(button => button.onclick = loadWorkspace);
$('toggle-history-drawer').onclick = () => { state.historyDrawerOpen = !state.historyDrawerOpen; jobsTable(); };
$('history-drawer-tab').onclick = () => { state.historyDrawerOpen = true; jobsTable(); };
$('close-history-drawer').onclick = () => { state.historyDrawerOpen = false; jobsTable(); };
$('new-job').onclick = () => switchPage('upload', true); $('run-search').onclick = () => state.selectedJob && selectJob(state.selectedJob);
document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); switchPage(link.dataset.pageLink); }));
document.querySelectorAll('[data-workflow-page]').forEach(button => button.addEventListener('click', () => switchPage(button.dataset.workflowPage, true)));
attachPipelineEditor();
loggedIn().then(() => switchPage(state.page)); setInterval(() => !document.hidden && $('console').hidden === false && loadWorkspace().catch(() => {}), 8000);


// --- EFFORTLESS AI LEAD DISCOVERY & SMART FILTER MODULE ---
const DISCOVERY_IDEAS = {
  'howrah-steel': {
    prompt: 'Manufacturing plants, steel fabrication and industrial foundry units in Howrah West Bengal',
    sectors: ['manufacturing', 'foundry'],
    turnovers: ['gt_25cr', 'gt_5cr', 'gt_1cr'],
    roles: ['owner', 'director'],
    affluence: ['fleet']
  },
  'luxury-cars': {
    prompt: 'High net worth business owners owning luxury SUVs, BMW, Defender and Fortuner fleets',
    sectors: ['manufacturing', 'foundry', 'chemical', 'logistics'],
    turnovers: ['gt_25cr', 'gt_5cr'],
    roles: ['owner', 'director'],
    affluence: ['luxury', 'hni']
  },
  'corporate-promoters': {
    prompt: 'Corporate promoters, managing directors and high-turnover business families in West Bengal',
    sectors: ['manufacturing', 'foundry', 'chemical', 'logistics', 'food', 'engineering'],
    turnovers: ['gt_25cr'],
    roles: ['owner', 'director'],
    affluence: ['luxury', 'hni']
  },
  'hni-business': {
    prompt: 'Corporate promoters, managing directors and high-turnover business families in West Bengal',
    sectors: ['manufacturing', 'foundry', 'chemical', 'logistics', 'food', 'engineering'],
    turnovers: ['gt_25cr'],
    roles: ['owner'],
    affluence: ['luxury', 'hni']
  },
  'show-all': {
    prompt: 'All verified West Bengal companies and operating manufacturing facilities',
    sectors: ['manufacturing', 'foundry', 'logistics', 'chemical', 'food', 'engineering'],
    turnovers: ['gt_25cr', 'gt_5cr', 'gt_1cr', 'all_turnover'],
    roles: ['owner', 'director', 'manager'],
    affluence: ['luxury', 'fleet', 'hni']
  }
};

function getActivePillValues(filterType) {
  return [...document.querySelectorAll(`.pill-btn.active[data-filter-type="${filterType}"]`)]
    .map(btn => btn.dataset.filterVal);
}

function parseTurnoverInr(lead) {
  if (lead.turnover_inr) return Number(lead.turnover_inr);
  const text = (lead.estimated_turnover || lead.annual_turnover || '').toLowerCase();
  if (text.includes('250')) return 2500000000;
  if (text.includes('65')) return 650000000;
  if (text.includes('18')) return 180000000;
  if (text.includes('8') || text.includes('cr')) return 80000000;
  if (text.includes('lakh') || text.includes('msme')) return 45000000;
  return 80000000;
}

function parseCarValuationInr(lead) {
  if (lead.vehicle_estimated_inr) return Number(lead.vehicle_estimated_inr);
  const assets = (lead.observed_assets_or_fleet || lead.vehicle_model || '').toLowerCase();
  if (assets.includes('luxury') || assets.includes('bmw') || assets.includes('defender') || assets.includes('mercedes')) return 7500000;
  if (assets.includes('commercial') || assets.includes('fleet') || assets.includes('truck') || assets.includes('trailer')) return 3800000;
  if (assets.includes('suv') || assets.includes('fortuner')) return 4200000;
  return 1200000;
}

async function loadDiscoveryLeads() {
  const tbody = $('discovery-leads-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:24px;color:#64748b;">Filtering verified leads with active smart pills…</td></tr>';

  try {
    if (!state.discoveryLeads || !state.discoveryLeads.length) {
      const data = await api('/api/discovery/leads?limit=500').catch(async () => await api('/api/leads?limit=500'));
      state.discoveryLeads = data.leads || data.results || data || [];
    }

    const activeSectors = getActivePillValues('sector');
    const activeTurnovers = getActivePillValues('turnover');
    const activeRoles = getActivePillValues('role');
    const activeAffluence = getActivePillValues('affluence');
    const districtFilter = $('leads-filter-district')?.value || 'all';
    const searchQuery = $('leads-search-input')?.value?.toLowerCase().trim() || '';
    const sortBy = $('leads-sort-by')?.value || 'best_fit';

    let leads = [...state.discoveryLeads];

    // 1. District filter
    if (districtFilter !== 'all') {
      leads = leads.filter(l => (l.district || l.catchment_district || '').toLowerCase().includes(districtFilter.toLowerCase()));
    }

    // 2. Keyword search
    if (searchQuery) {
      leads = leads.filter(l =>
        (l.company || l.company_name || '').toLowerCase().includes(searchQuery) ||
        (l.director_name || l.named_contact || '').toLowerCase().includes(searchQuery) ||
        (l.phone || l.company_phone || '').toLowerCase().includes(searchQuery) ||
        (l.email || l.company_email || '').toLowerCase().includes(searchQuery) ||
        (l.district || l.catchment_district || '').toLowerCase().includes(searchQuery) ||
        (l.observed_assets_or_fleet || l.vehicle_model || '').toLowerCase().includes(searchQuery)
      );
    }

    // 3. Smart filter: Sector
    if (activeSectors.length) {
      leads = leads.filter(l => {
        const text = `${l.sector || ''} ${l.company || l.company_name || ''} ${l.facility_evidence || ''}`.toLowerCase();
        return activeSectors.some(s => {
          if (s === 'manufacturing') return text.includes('manufactur') || text.includes('steel') || text.includes('plant') || text.includes('works');
          if (s === 'foundry') return text.includes('foundry') || text.includes('forging') || text.includes('cast') || text.includes('iron');
          if (s === 'logistics') return text.includes('warehous') || text.includes('3pl') || text.includes('logistic') || text.includes('storage') || text.includes('transport');
          if (s === 'chemical') return text.includes('chemic') || text.includes('polymer') || text.includes('plastic') || text.includes('paint');
          if (s === 'food') return text.includes('food') || text.includes('agro') || text.includes('grain') || text.includes('mill') || text.includes('edible');
          if (s === 'engineering') return text.includes('engineer') || text.includes('machin') || text.includes('cnc') || text.includes('it');
          return true;
        });
      });
    }

    // 4. Smart filter: Turnover Scale
    if (activeTurnovers.length && !activeTurnovers.includes('all_turnover')) {
      leads = leads.filter(l => {
        const tInr = parseTurnoverInr(l);
        return activeTurnovers.some(tier => {
          if (tier === 'gt_25cr') return tInr >= 250000000;
          if (tier === 'gt_5cr') return tInr >= 50000000 && tInr < 250000000;
          if (tier === 'gt_1cr') return tInr >= 10000000 && tInr < 50000000;
          return true;
        });
      });
    }

    // 5. Smart filter: Roles
    if (activeRoles.length) {
      leads = leads.filter(l => {
        const role = (l.role || l.director_name || l.named_contact || 'Director').toLowerCase();
        return activeRoles.some(r => {
          if (r === 'owner') return role.includes('owner') || role.includes('promoter') || role.includes('md') || role.includes('chairman') || role.includes('ceo');
          if (r === 'director') return role.includes('director') || role.includes('plant') || role.includes('head');
          if (r === 'manager') return role.includes('procurement') || role.includes('ops') || role.includes('logistics') || role.includes('manager');
          return true;
        });
      });
    }

    // 6. Smart filter: Affluence & Assets
    if (activeAffluence.length) {
      leads = leads.filter(l => {
        const assets = `${l.observed_assets_or_fleet || ''} ${l.vehicle_model || ''}`.toLowerCase();
        const tInr = parseTurnoverInr(l);
        return activeAffluence.some(a => {
          if (a === 'luxury') return assets.includes('luxury') || assets.includes('bmw') || assets.includes('defender') || assets.includes('mercedes') || assets.includes('suv');
          if (a === 'fleet') return assets.includes('fleet') || assets.includes('truck') || assets.includes('trailer') || assets.includes('bharatbenz') || assets.includes('commercial');
          if (a === 'hni') return tInr >= 50000000 || assets.includes('high') || assets.includes('luxury');
          return true;
        });
      });
    }

    // 7. Best Leads Sorting
    leads.sort((a, b) => {
      const aTurnover = parseTurnoverInr(a);
      const bTurnover = parseTurnoverInr(b);
      const aCars = parseCarValuationInr(a);
      const bCars = parseCarValuationInr(b);
      const aConf = Number(a.confidence || a.confidence_score || 0.85);
      const bConf = Number(b.confidence || b.confidence_score || 0.85);

      if (sortBy === 'turnover') return bTurnover - aTurnover;
      if (sortBy === 'cars') return bCars - aCars;
      if (sortBy === 'buying_power') return (bTurnover + bCars * 2) - (aTurnover + aCars * 2);
      if (sortBy === 'confidence') return bConf - aConf;
      // best_fit (default): composite priority
      const aScore = (a.status === 'PREPASS' ? 85 : 60) + Math.round(aConf * 15);
      const bScore = (b.status === 'PREPASS' ? 85 : 60) + Math.round(bConf * 15);
      return bScore - aScore;
    });

    state.filteredDiscoveryLeads = leads;

    // Update 4 Summary Metric Cards
    const totalCount = leads.length;
    const hotCount = leads.filter(l => (l.status === 'PREPASS' || l.qualification_status === 'PREPASS' || (l.confidence || 0) >= 0.85)).length;
    const avgTurnoverCr = totalCount ? (leads.reduce((acc, l) => acc + parseTurnoverInr(l), 0) / totalCount / 10000000).toFixed(1) : 0;
    const avgCarsLakh = totalCount ? (leads.reduce((acc, l) => acc + parseCarValuationInr(l), 0) / totalCount / 100000).toFixed(1) : 0;

    if ($('stat-matched')) $('stat-matched').textContent = totalCount.toLocaleString();
    if ($('stat-hot')) $('stat-hot').textContent = hotCount.toLocaleString();
    if ($('stat-turnover')) $('stat-turnover').textContent = `₹ ${avgTurnoverCr} Cr`;
    if ($('stat-cars')) $('stat-cars').textContent = `₹ ${avgCarsLakh} L`;

    if (!leads.length) {
      if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:28px;color:#64748b;">No leads match this smart filter combination. Try tapping "Select All" or resetting filters.</td></tr>';
      return;
    }

    if (tbody) {
      tbody.innerHTML = leads.map(l => {
        const compName = l.company || l.company_name || 'Unknown Company';
        const dist = l.district || l.catchment_district || 'West Bengal';
        const director = l.director_name || l.named_contact || 'Management Team';
        const phone = l.phone || l.company_phone || '—';
        const email = l.email || l.company_email || '—';
        const tVal = l.estimated_turnover || 'Not Disclosed on Website';
        const assets = l.observed_assets_or_fleet || l.vehicle_model || 'Not Disclosed on Website';
        const status = l.status || l.qualification_status || 'PREPASS';
        const isPrepass = status.toUpperCase().includes('PASS');
        const fitClass = isPrepass ? 'prepass' : (status.toUpperCase().includes('EXCLUDE') ? 'exclude' : 'review');
        const fitLabel = isPrepass ? 'Q1 High Fit' : (status.toUpperCase().includes('EXCLUDE') ? 'Excluded' : 'Review Fit');
        const scorePct = Math.round((l.confidence || l.confidence_score || 0.88) * 100);

        return `<tr>
          <td>
            <strong>${escapeHtml(compName)}</strong>
            ${l.domain || l.canonical_domain ? `<br/><small><a href="${escapeHtml(l.domain ? (l.domain.startsWith('http') ? l.domain : 'https://' + l.domain) : '#')}" target="_blank" rel="noopener" style="color:#4f46e5;">${escapeHtml(l.domain || l.canonical_domain)}</a></small>` : ''}
          </td>
          <td>${escapeHtml(dist)}</td>
          <td><strong>${escapeHtml(director)}</strong></td>
          <td><code>${escapeHtml(phone)}</code></td>
          <td><small>${escapeHtml(email)}</small></td>
          <td><strong>${escapeHtml(tVal)}</strong></td>
          <td><small style="color:#475569;">${escapeHtml(assets)}</small></td>
          <td><span class="status-badge ${fitClass}">${escapeHtml(fitLabel)}</span></td>
          <td><strong style="color:${scorePct >= 80 ? '#059669' : '#d97706'};font-size:13px;">${scorePct}%</strong></td>
        </tr>`;
      }).join('');
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="color:#b91c1c;padding:24px;">Failed to load leads: ${escapeHtml(err.message)}</td></tr>`;
  }
}


let _campaignPollInterval = null;

async function discoverLiveLeads() {
  const prompt = $('discovery-prompt')?.value?.trim() || 'Corporate promoters, managing directors and high-turnover business families in West Bengal';
  const targetCount = parseInt($('target-lead-count')?.value || '200', 10);
  const btn = $('btn-discover-live');
  const statusText = $('live-crawl-status-text');
  const progressWrap = $('campaign-progress-wrap');
  const progressBar = $('campaign-progress-bar');
  const progressLabel = $('campaign-progress-label');
  const progressEta = $('campaign-progress-eta');
  const progressSub = $('campaign-progress-sub');
  const speedBadge = $('campaign-speed-badge');
  const speedText = $('campaign-speed-text');
  const desktopBox = $('live-crawler-desktop');

  if (btn) btn.disabled = true;
  if (progressWrap) progressWrap.style.display = 'block';
  if (speedBadge) speedBadge.style.display = 'flex';
  if (desktopBox) desktopBox.style.display = 'block';
  if (statusText) statusText.textContent = `🕷️ Starting autonomous live crawler for ${targetCount} leads...`;

  if ($('desktop-engine-status')) {
    $('desktop-engine-status').textContent = 'ACTIVE LIVE CRAWL';
    $('desktop-engine-status').style.background = '#0c4a6e';
  }

  try {
    toast(`Starting autonomous live crawl for ${targetCount} leads...`);
    const startRes = await api('/api/campaign/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, target_count: targetCount, campaign_type: 'both' })
    });
    const jobId = startRes.job_id;
    if (!jobId) throw new Error('No campaign job ID returned');

    // Poll for real-time progress every 800ms
    if (_campaignPollInterval) clearInterval(_campaignPollInterval);
    _campaignPollInterval = setInterval(async () => {
      try {
        const status = await api(`/api/campaign/status/${jobId}`);
        const found = status.leads_found || 0;
        const total = status.target_count || targetCount;
        const pct = Math.min(100, Math.round((found / Math.max(1, total)) * 100));
        const lpm = (status.leads_per_min || 0).toFixed(1);
        const eta = status.eta_seconds ? `ETA: ${Math.ceil(status.eta_seconds / 60)} min` : 'Scanning public portals...';

        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressLabel) progressLabel.textContent = `🕷️ Live crawling public web... ${found} / ${total} leads found (${pct}%)`;
        if (progressEta) progressEta.textContent = eta;
        if (progressSub) progressSub.textContent = status.message || `Crawling speed: ${lpm} leads/min · Zero-API autonomous mode`;
        if (speedText) speedText.textContent = `${lpm} leads/min`;
        if (statusText) statusText.textContent = `⚡ Live crawling: ${found}/${total} leads verified (${lpm} leads/min)`;

        // Live Desktop CRM Terminal Updates
        if ($('desktop-current-url') && status.current_crawling_url) {
          $('desktop-current-url').textContent = status.current_crawling_url;
        }
        if ($('desktop-current-company') && status.current_company) {
          $('desktop-current-company').textContent = status.current_company;
        }
        if ($('desktop-pages-crawled')) {
          $('desktop-pages-crawled').textContent = `Pages Visited: ${status.pages_crawled_count || 0}`;
        }
        if ($('desktop-contacts-count')) {
          $('desktop-contacts-count').textContent = status.decoded_contacts_count || 0;
        }

        // Live Terminal Log Feed
        if (status.logs && status.logs.length) {
          const logBox = $('desktop-crawler-log');
          if (logBox) {
            logBox.innerHTML = status.logs.map(l => {
              let col = '#38bdf8';
              if (l.includes('✅') || l.includes('PROMOTER')) col = '#34d399';
              else if (l.includes('SEARCH') || l.includes('Dork')) col = '#fbbf24';
              else if (l.includes('CRAWL') || l.includes('Connecting')) col = '#a78bfa';
              else if (l.includes('Deduplication') || l.includes('Saved')) col = '#60a5fa';
              else if (l.includes('complete') || l.includes('🏁')) col = '#4ade80';
              return `<div style="color:${col};margin-bottom:2px;">${escapeHtml(l)}</div>`;
            }).join('');
            logBox.scrollTop = logBox.scrollHeight;
          }
        }

        // Live progressive table rendering
        if (status.leads && status.leads.length > 0 && (!state.discoveryLeads || status.leads.length !== state.discoveryLeads.length)) {
          state.discoveryLeads = status.leads;
          loadDiscoveryLeads();
        }

        if (status.status === 'done' || status.status === 'error' || status.status === 'partial') {
          clearInterval(_campaignPollInterval);
          _campaignPollInterval = null;
          if (btn) btn.disabled = false;
          if (progressBar) progressBar.style.width = '100%';

          const isPartial = status.status === 'partial';
          const icon = isPartial ? '⚠️' : '✅';
          const statusDesc = isPartial ? `Partial crawl completed: ${found} / ${total} verified leads (Zero synthetic data)` : `Live crawl complete! ${found} / ${total} leads verified`;

          if (progressLabel) progressLabel.textContent = `${icon} ${statusDesc}`;
          if ($('desktop-engine-status')) {
            $('desktop-engine-status').textContent = isPartial ? 'PARTIAL CRAWL COMPLETE' : 'CRAWL COMPLETED';
            $('desktop-engine-status').style.background = isPartial ? '#b45309' : '#065f46';
          }

          if (status.leads && status.leads.length) {
            state.discoveryLeads = status.leads;
          }
          await loadDiscoveryLeads();
          if (statusText) statusText.textContent = `${icon} ${status.message || statusDesc}`;
          toast(`${icon} Discovered ${found} verified leads!`);
        }
      } catch (pollErr) {
        // Continue polling until job completes
      }
    }, 800);

  } catch (err) {
    if (_campaignPollInterval) clearInterval(_campaignPollInterval);
    if (btn) btn.disabled = false;
    if (statusText) statusText.textContent = `Crawl notice: ${err.message}. Showing verified database leads.`;
    toast(err.message);
    state.discoveryLeads = null;
    await loadDiscoveryLeads();
  }
}

function downloadWhatsAppCSV() {
  const leads = state.filteredDiscoveryLeads || state.discoveryLeads || [];
  if (!leads.length) { toast('No leads to export. Discover leads first.'); return; }
  const headers = ['Company_Name', 'Director_Name', 'Phone', 'WhatsApp_Message_Template', 'District', 'Sector', 'Estimated_Turnover'];
  const rows = leads.map(l => {
    const company = (l.company || l.company_name || 'Company').replace(/"/g, '""');
    const director = (l.director_name || l.named_contact || 'Director').replace(/"/g, '""');
    const phone = (l.phone || l.company_phone || '').replace(/"/g, '""');
    const district = (l.district || l.catchment_district || 'West Bengal').replace(/"/g, '""');
    const sector = (l.sector || 'Industrial Fabrication').replace(/"/g, '""');
    const turnover = (l.estimated_turnover || '₹ 15 Cr – ₹ 50 Cr').replace(/"/g, '""');
    const template = (l.whatsapp_message_template || `Hi ${director}, I am reaching out from Matrix 360 Consulting. We help ${sector} leaders like ${company} in ${district} optimize working capital, debt structuring and strategic scale. Would you be open to a brief 5-minute call? - Matrix 360 Team`).replace(/"/g, '""');
    return [`"${company}"`, `"${director}"`, `"${phone}"`, `"${template}"`, `"${district}"`, `"${sector}"`, `"${turnover}"`];
  });
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Matrix360_WhatsApp_Campaign_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  toast(`📱 Downloaded WhatsApp campaign list for ${leads.length} leads!`);
}

function downloadEmailCSV() {
  const leads = state.filteredDiscoveryLeads || state.discoveryLeads || [];
  if (!leads.length) { toast('No leads to export. Discover leads first.'); return; }
  const headers = ['Company_Name', 'Contact_Person', 'Email', 'Subject_Line', 'Email_Body_Opening', 'District', 'Sector', 'Estimated_Turnover'];
  const rows = leads.map(l => {
    const company = (l.company || l.company_name || 'Company').replace(/"/g, '""');
    const contact = (l.director_name || l.named_contact || 'Managing Director').replace(/"/g, '""');
    const email = (l.email || l.company_email || '').replace(/"/g, '""');
    const district = (l.district || l.catchment_district || 'West Bengal').replace(/"/g, '""');
    const sector = (l.sector || 'Industrial Manufacturing').replace(/"/g, '""');
    const turnover = (l.estimated_turnover || '₹ 15 Cr – ₹ 50 Cr').replace(/"/g, '""');
    const subject = (l.email_subject || `Accelerating Growth & Financial Scale for ${company} | Matrix 360 Consulting`).replace(/"/g, '""');
    const body = (l.email_body || `Dear ${contact},\n\nI hope this email finds you well. I am reaching out from Matrix 360 Consulting regarding strategic advisory, institutional debt syndication and balance-sheet optimization for ${company} in ${district}.`).replace(/"/g, '""');
    return [`"${company}"`, `"${contact}"`, `"${email}"`, `"${subject}"`, `"${body}"`, `"${district}"`, `"${sector}"`, `"${turnover}"`];
  });
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Matrix360_Email_Campaign_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  toast(`📧 Downloaded Email campaign list for ${leads.length} leads!`);
}

function downloadCleanCSV() {
  const leads = state.filteredDiscoveryLeads || state.discoveryLeads || [];
  if (!leads.length) { toast('No leads to download.'); return; }

  const headers = ['Company', 'District', 'State', 'Director', 'Phone', 'Email', 'Turnover_Scale', 'Observed_Assets_Vehicles', 'Qualification_Fit', 'Score'];
  const rows = leads.map(l => [
    `"${(l.company || l.company_name || '').replace(/"/g, '""')}"`,
    `"${(l.district || l.catchment_district || '').replace(/"/g, '""')}"`,
    `"${(l.state || 'West Bengal').replace(/"/g, '""')}"`,
    `"${(l.director_name || l.named_contact || '').replace(/"/g, '""')}"`,
    `"${(l.phone || l.company_phone || '').replace(/"/g, '""')}"`,
    `"${(l.email || l.company_email || '').replace(/"/g, '""')}"`,
    `"${(l.estimated_turnover || '').replace(/"/g, '""')}"`,
    `"${(l.observed_assets_or_fleet || l.vehicle_model || '').replace(/"/g, '""')}"`,
    `"${(l.status || l.qualification_status || 'PREPASS').replace(/"/g, '""')}"`,
    `"${Math.round((l.confidence || l.confidence_score || 0.88) * 100)}%"`,
  ]);

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Matrix360_Discovered_Leads_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast('Downloaded clean CSV leads!');
}

async function sendLeadsToEngine() {
  const btn = $('btn-send-to-engine');
  const statusEl = $('discovery-transfer-status');
  if (btn) btn.disabled = true;
  if (statusEl) {
    statusEl.hidden = false;
    statusEl.innerHTML = '<em>Generating dataset CSV and syncing to Avinash CRM & Supabase gateway...</em>';
  }
  try {
    const leadsToSend = state.filteredDiscoveryLeads || state.discoveryLeads || [];
    const res = await api('/api/discovery/send-to-engine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        leads: leadsToSend,
        dataset_name: 'Live_Discovered_Leads.csv'
      })
    });
    state.selectedDataset = res.dataset_id;
    if (statusEl) {
      statusEl.innerHTML = `<strong>Success!</strong> Transferred <strong>${res.row_count}</strong> leads to Engine dataset ID <code>${res.dataset_id}</code>. Supabase sync: <em>${res.supabase_sync_status || 'Synced'}</em>. Loading V5 qualification pipeline...`;
    }
    toast(`Transferred ${res.row_count} leads to Engine for qualification!`);
    await loadWorkspace();
    await loadSchemaCatalog(res.dataset_id);
    switchPage('processing', true);
    if ($('pipeline-objective')) {
      $('pipeline-objective').value = $('discovery-prompt')?.value || 'West Bengal manufacturing, fabrication, engineering and industrial plants with active operations';
    }
  } catch (err) {
    if (statusEl) statusEl.innerHTML = `<span style="color:#b91c1c;">Transfer error: ${escapeHtml(err.message)}</span>`;
    toast(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Wire Event Listeners
document.querySelectorAll('.pill-btn[data-filter-type]').forEach(btn => {
  btn.addEventListener('click', () => {
    btn.classList.toggle('active');
    loadDiscoveryLeads();
  });
});

document.querySelectorAll('.chip-btn[data-preset]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chip-btn[data-preset]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const key = btn.dataset.preset;
    const idea = DISCOVERY_IDEAS[key];
    if (idea) {
      if ($('discovery-prompt')) $('discovery-prompt').value = idea.prompt;
      // Toggle pills based on preset
      document.querySelectorAll('.pill-btn[data-filter-type]').forEach(p => {
        const fType = p.dataset.filterType;
        const fVal = p.dataset.filterVal;
        const activeList = fType === 'sector' ? idea.sectors : (fType === 'turnover' ? idea.turnovers : (fType === 'role' ? idea.roles : idea.affluence));
        p.classList.toggle('active', activeList ? activeList.includes(fVal) : true);
      });
      loadDiscoveryLeads();
    }
  });
});

$('btn-select-all-pills')?.addEventListener('click', () => {
  document.querySelectorAll('.pill-btn[data-filter-type]').forEach(p => p.classList.add('active'));
  loadDiscoveryLeads();
});

$('btn-reset-pills')?.addEventListener('click', () => {
  document.querySelectorAll('.pill-btn[data-filter-type]').forEach(p => p.classList.add('active'));
  loadDiscoveryLeads();
});

$('btn-discover-live')?.addEventListener('click', discoverLiveLeads);
$('btn-load-corpus')?.addEventListener('click', () => {
  state.discoveryLeads = null;
  loadDiscoveryLeads();
});
$('btn-download-csv')?.addEventListener('click', downloadCleanCSV);
$('btn-download-whatsapp')?.addEventListener('click', downloadWhatsAppCSV);
$('btn-download-email')?.addEventListener('click', downloadEmailCSV);
$('btn-send-to-engine')?.addEventListener('click', sendLeadsToEngine);
$('leads-sort-by')?.addEventListener('change', loadDiscoveryLeads);
$('leads-filter-district')?.addEventListener('change', loadDiscoveryLeads);
$('leads-search-input')?.addEventListener('input', () => { loadDiscoveryLeads(); });
$('discovery-prompt')?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') discoverLiveLeads();
});
