const state = { files: [], datasets: [], jobs: [], selectedDataset: null, selectedJob: null, page: 'dashboard', advancedFilters: [], filterMetadata: null, filterMetadataJob: null };
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

function switchPage(page) {
  state.page = page;
  document.querySelectorAll('[data-page]').forEach(section => { section.hidden = section.dataset.page !== page; });
  document.querySelectorAll('[data-page-link]').forEach(link => link.classList.toggle('active', link.dataset.pageLink === page));
  if (page === 'jobs') renderJobLog();
  if ((page === 'results' || page === 'exports') && state.selectedJob) selectJob(state.selectedJob);
}

function setFiles(files) {
  state.files = [...files]; $('upload').disabled = !state.files.length;
  $('file-tree').className = 'file-tree';
  $('file-tree').innerHTML = state.files.length ? state.files.map(f => `<div><strong>${escapeHtml(f.webkitRelativePath || f.name)}</strong><span>${(f.size / 1024).toFixed(1)} KB</span></div>`).join('') : 'No files selected.';
}
function datasetRadio() {
  $('dataset-picker').innerHTML = state.datasets.length ? state.datasets.map(d => `<label class="dataset"><input type="radio" name="dataset" value="${d.id}" ${state.selectedDataset === d.id ? 'checked' : ''}/><span><strong>${d.files.length} file${d.files.length === 1 ? '' : 's'}</strong><small>${d.files.map(f => escapeHtml(f.relative_path)).join(', ')}</small></span></label>`).join('') : 'Upload a dataset to begin.';
  document.querySelectorAll('input[name=dataset]').forEach(input => input.addEventListener('change', e => { state.selectedDataset = e.target.value; $('start-job').disabled = false; }));
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
  $('filter-hint').textContent = `${available.length} normalized fields and ${imported.length} additional imported columns are available for this processed dataset.`;
  $('vehicle-filter-notice').hidden = !available.some(item => item.group === 'Vehicle (observed data only)');
  $('vehicle-filter-notice').textContent = metadata.vehicle_notice;
  renderAdvancedFilters();
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
  const [datasets, jobs, audit] = await Promise.all([api('/api/v1/datasets'), api('/api/v1/jobs'), api('/api/v1/audit')]);
  state.datasets = datasets.datasets; state.jobs = jobs.jobs; $('dataset-count').textContent = state.datasets.length; datasetRadio(); jobsTable(); renderJobLog();
  $('audit-list').innerHTML = audit.events.length ? audit.events.map(e => `<div class="audit"><strong>${escapeHtml(e.action)}</strong><span>${escapeHtml(e.actor)} · ${new Date(e.created_at).toLocaleString()}</span></div>`).join('') : 'No activity yet.';
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
  $('export-list').innerHTML = exports.exports.length ? exportSummary + exports.exports.map(e => `<a class="export" href="/api/v1/exports/${e.id}/download"><strong>${escapeHtml(e.name)}</strong><span>${(e.size_bytes / 1024).toFixed(1)} KB · SHA-256 ${escapeHtml(e.sha256.slice(0, 12))}…</span></a>`).join('') : exportSummary + 'No exports available until the job completes.';
}
async function loggedIn() {
  const session = await api('/api/v1/auth/session');
  if (!session.authenticated) return false;
  const user = session.user; $('workspace').textContent = `${user.tenant_id} / ${user.role}`; $('login-panel').hidden = true; $('console').hidden = false; await loadWorkspace(); return true;
}
$('login-form').addEventListener('submit', async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); try { const user = await api('/api/v1/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) }); $('workspace').textContent = `${user.tenant_id} / ${user.role}`; $('login-panel').hidden = true; $('console').hidden = false; await loadWorkspace(); } catch (error) { $('login-error').textContent = error.message; } });
$('logout').addEventListener('click', async () => { await api('/api/v1/auth/logout', {method:'POST'}); location.reload(); });
$('choose-files').onclick = () => $('files').click(); $('choose-folder').onclick = () => $('folder').click(); $('files').onchange = e => setFiles(e.target.files); $('folder').onchange = e => setFiles(e.target.files);
$('dropzone').addEventListener('dragover', e => { e.preventDefault(); $('dropzone').classList.add('dragging'); }); $('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('dragging')); $('dropzone').addEventListener('drop', e => { e.preventDefault(); $('dropzone').classList.remove('dragging'); setFiles(e.dataTransfer.files); });
$('upload-form').addEventListener('submit', async event => { event.preventDefault(); if (!state.files.length) return; const form = new FormData(); state.files.forEach(file => form.append('files', file)); form.append('relative_paths', JSON.stringify(state.files.map(file => file.webkitRelativePath || file.name))); $('upload').disabled = true; try { const result = await api('/api/v1/datasets', {method:'POST', body:form}); state.selectedDataset = result.dataset_id; $('inspection').hidden = false; $('inspection').innerHTML = result.files.map(file => `<div><strong>${escapeHtml(file.name)}</strong><p>SHA-256 ${file.sha256.slice(0,16)}… · ${file.size_bytes} bytes</p><code>${escapeHtml(file.inspection.headers.join(' | '))}</code></div>`).join(''); await loadWorkspace(); switchPage('processing'); toast('Upload complete. Select the dataset, then click Start processing.'); } catch (error) { toast(error.message); } finally { $('upload').disabled = false; } });
function updateAdvancedFilterValueInput() {
  const noValue = ['is_present','is_empty'].includes($('advanced-filter-operator').value);
  $('advanced-filter-value-label').hidden = noValue;
  $('advanced-filter-value').disabled = noValue;
}
$('advanced-filter-operator').addEventListener('change', updateAdvancedFilterValueInput);
$('add-advanced-filter').addEventListener('click', () => {
  const field = $('advanced-filter-field').value;
  const operator = $('advanced-filter-operator').value;
  const values = $('advanced-filter-value').value.split(',').map(value => value.trim()).filter(Boolean);
  if (!field) { toast('Choose a field to filter.'); return; }
  if (!['is_present','is_empty'].includes(operator) && !values.length) { toast('Enter one or more comma-separated values.'); return; }
  state.advancedFilters.push({field, operator, values});
  $('advanced-filter-value').value = ''; renderAdvancedFilters(); state.selectedJob && selectJob(state.selectedJob);
});
$('start-job').addEventListener('click', async () => { if (!state.selectedDataset) return; const clientProfiles = selected('process-profile-filter'); if (!clientProfiles.length) { toast('Choose at least one client export file.'); return; } $('start-job').disabled = true; try { const job = await api('/api/v1/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dataset_id: state.selectedDataset, idempotency_key: crypto.randomUUID(), client_profiles: clientProfiles, districts: selected('process-district-filter')})}); state.selectedJob = job.job_id; await loadWorkspace(); switchPage('jobs'); toast(`Job queued: ${job.job_id.slice(0,8)}. Follow its live processing log here.`); } catch (error) { toast(error.message); $('start-job').disabled = false; } });
const districtOptions = districts.map(district => `<option value="${escapeHtml(district)}">${escapeHtml(district)}</option>`).join('');
$('district-filter').innerHTML = districtOptions; $('process-district-filter').innerHTML = districtOptions;
document.querySelectorAll('.refresh').forEach(button => button.onclick = loadWorkspace); $('new-job').onclick = () => switchPage('upload'); $('run-search').onclick = () => state.selectedJob && selectJob(state.selectedJob);
document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); switchPage(link.dataset.pageLink); }));
loggedIn().then(() => switchPage(state.page)); setInterval(() => !document.hidden && $('console').hidden === false && loadWorkspace().catch(() => {}), 8000);

