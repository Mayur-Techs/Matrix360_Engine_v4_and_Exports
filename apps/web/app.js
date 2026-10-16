const state = { files: [], datasets: [], jobs: [], selectedDataset: null, selectedJob: null };
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

function setFiles(files) {
  state.files = [...files]; $('upload').disabled = !state.files.length;
  $('file-tree').className = 'file-tree';
  $('file-tree').innerHTML = state.files.length ? state.files.map(f => `<div><strong>${escapeHtml(f.webkitRelativePath || f.name)}</strong><span>${(f.size / 1024).toFixed(1)} KB</span></div>`).join('') : 'No files selected.';
}
function datasetRadio() {
  $('dataset-picker').innerHTML = state.datasets.length ? state.datasets.map(d => `<label class="dataset"><input type="radio" name="dataset" value="${d.id}" ${state.selectedDataset === d.id ? 'checked' : ''}/><span><strong>${d.files.length} file${d.files.length === 1 ? '' : 's'}</strong><small>${d.files.map(f => escapeHtml(f.relative_path)).join(', ')}</small></span></label>`).join('') : 'Upload a dataset to begin.';
  document.querySelectorAll('input[name=dataset]').forEach(input => input.addEventListener('change', e => { state.selectedDataset = e.target.value; $('start-job').disabled = false; }));
}
function jobsTable() {
  $('jobs').innerHTML = state.jobs.length ? `<div class="job-list">${state.jobs.map(j => {
    const percent = Number.isFinite(j.progress_percent) ? j.progress_percent : 0;
    const detail = j.status === 'failed' ? `${j.error_code || 'Processing error'}${j.error_detail ? ` · ${j.error_detail}` : ''}` : `${j.progress_phase || j.status} · ${percent}%`;
    return `<button class="job ${j.id === state.selectedJob ? 'selected' : ''}" data-job="${j.id}"><span><strong>${j.status.replace('_', ' ')}</strong><small>${escapeHtml(detail)}</small><i class="job-progress"><i style="width:${Math.max(0, Math.min(100, percent))}%"></i></i><small>${new Date(j.created_at).toLocaleString()}</small></span><span>${j.report?.active_rows ?? '—'} rows</span></button>`;
  }).join('')}</div>` : 'No jobs yet.';
  document.querySelectorAll('[data-job]').forEach(button => button.addEventListener('click', () => selectJob(button.dataset.job)));
  $('active-count').textContent = state.jobs.filter(j => ['queued','running'].includes(j.status)).length;
  $('completed-count').textContent = state.jobs.filter(j => ['completed','needs_review'].includes(j.status)).length;
  $('review-count').textContent = state.jobs.filter(j => j.status === 'needs_review').length;
}
async function loadWorkspace() {
  const [datasets, jobs, audit] = await Promise.all([api('/api/v1/datasets'), api('/api/v1/jobs'), api('/api/v1/audit')]);
  state.datasets = datasets.datasets; state.jobs = jobs.jobs; $('dataset-count').textContent = state.datasets.length; datasetRadio(); jobsTable();
  $('audit-list').innerHTML = audit.events.length ? audit.events.map(e => `<div class="audit"><strong>${escapeHtml(e.action)}</strong><span>${escapeHtml(e.actor)} · ${new Date(e.created_at).toLocaleString()}</span></div>`).join('') : 'No activity yet.';
}
async function selectJob(jobId) {
  state.selectedJob = jobId; jobsTable();
  const selected = id => [...$(id).selectedOptions].map(option => option.value || option.textContent);
  const filter = new URLSearchParams({limit:'50', search:$('search').value});
  selected('geo-filter').forEach(value => filter.append('geo_statuses', value));
  selected('district-filter').forEach(value => filter.append('districts', value));
  selected('profile-filter').forEach(value => filter.append('client_profiles', value));
  const [result, exports] = await Promise.all([api(`/api/v1/jobs/${jobId}/results?${filter}`), api(`/api/v1/jobs/${jobId}/exports`)]);
  $('result-meta').textContent = `${result.total} matching records · ${result.status}`;
  const columns = ['name','company','city','state','geo_status','lakhotia_class','shree_class','vrindavan_class'];
  $('result-head').innerHTML = `<tr>${columns.map(c => `<th>${c.replaceAll('_', ' ')}</th>`).join('')}</tr>`;
  $('result-body').innerHTML = result.rows.map(row => `<tr>${columns.map(c => `<td>${escapeHtml(row[c])}</td>`).join('')}</tr>`).join('') || '<tr><td colspan="8">No records available.</td></tr>';
  $('export-list').innerHTML = exports.exports.length ? exports.exports.map(e => `<a class="export" href="/api/v1/exports/${e.id}/download"><strong>${escapeHtml(e.name)}</strong><span>${(e.size_bytes / 1024).toFixed(1)} KB · SHA-256 ${escapeHtml(e.sha256.slice(0, 12))}…</span></a>`).join('') : 'No exports available until the job completes.';
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
$('upload-form').addEventListener('submit', async event => { event.preventDefault(); if (!state.files.length) return; const form = new FormData(); state.files.forEach(file => form.append('files', file)); form.append('relative_paths', JSON.stringify(state.files.map(file => file.webkitRelativePath || file.name))); $('upload').disabled = true; try { const result = await api('/api/v1/datasets', {method:'POST', body:form}); state.selectedDataset = result.dataset_id; $('inspection').hidden = false; $('inspection').innerHTML = result.files.map(file => `<div><strong>${escapeHtml(file.name)}</strong><p>SHA-256 ${file.sha256.slice(0,16)}… · ${file.size_bytes} bytes</p><code>${escapeHtml(file.inspection.headers.join(' | '))}</code></div>`).join(''); toast('Upload complete. Review the sampled schema, then start processing.'); await loadWorkspace(); } catch (error) { toast(error.message); } finally { $('upload').disabled = false; } });
$('start-job').addEventListener('click', async () => { if (!state.selectedDataset) return; try { const job = await api('/api/v1/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dataset_id: state.selectedDataset, idempotency_key: crypto.randomUUID()})}); toast(`Job queued: ${job.job_id.slice(0,8)}. Progress will appear here automatically.`); await loadWorkspace(); } catch (error) { toast(error.message); } });
$('district-filter').innerHTML = districts.map(district => `<option value="${escapeHtml(district)}">${escapeHtml(district)}</option>`).join('');
document.querySelectorAll('.refresh').forEach(button => button.onclick = loadWorkspace); $('new-job').onclick = () => $('library').scrollIntoView({behavior:'smooth'}); $('run-search').onclick = () => state.selectedJob && selectJob(state.selectedJob);
loggedIn(); setInterval(() => !document.hidden && $('console').hidden === false && loadWorkspace().catch(() => {}), 8000);

