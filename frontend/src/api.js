const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchTenants() {
  const res = await fetch(`${API_BASE_URL}/tenants`);
  if (!res.ok) throw new Error('Failed to fetch tenants');
  return res.json();
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Login failed');
  return data;
}

export async function registerUser(payload) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Registration failed');
  return data;
}

export async function lookupLead(mobile, organizationId) {
  const res = await fetch(`${API_BASE_URL}/leads/lookup?mobile=${encodeURIComponent(mobile)}&organization_id=${organizationId}`);
  if (!res.ok) {
    if (res.status === 404) return null;
    const data = await res.json();
    throw new Error(data.detail || 'Lookup failed');
  }
  return res.json();
}

export async function submitLead(serviceName, leadData, organizationId) {
  const res = await fetch(`${API_BASE_URL}/leads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      service_name: serviceName,
      organization_id: organizationId,
      data: leadData,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    if (res.status === 422 && data.detail?.errors) {
      throw new Error(data.detail.errors.join(' '));
    }
    throw new Error(data.detail || 'Failed to submit requirement');
  }
  return data;
}

export async function downloadExcelExport(organizationId, filename = 'leads_export.xlsx') {
  const res = await fetch(`${API_BASE_URL}/leads/export?organization_id=${organizationId}`);
  if (!res.ok) throw new Error('Failed to download export');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function sendChatMessage(message) {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Chat request failed');
  return data.reply;
}
