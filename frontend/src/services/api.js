const API_BASE_URL = "http://127.0.0.1:8000";

/*
|--------------------------------------------------------------------------
| Generic API helper
|--------------------------------------------------------------------------
*/

async function handleResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      if (contentType.includes("application/json")) {
        const data = await response.json();
        message = data.detail || data.message || message;
      } else {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
    } catch {
      // Keep default error message
    }

    throw new Error(message);
  }

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response;
}

/*
|--------------------------------------------------------------------------
| Backend Health
|--------------------------------------------------------------------------
*/

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Inventory Root
|--------------------------------------------------------------------------
*/

export async function getInventoryStatus() {
  const response = await fetch(`${API_BASE_URL}/inventory/`);

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Clean Inventory
|--------------------------------------------------------------------------
*/

export async function cleanInventory(file) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/inventory/clean`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Compare Inventory
|--------------------------------------------------------------------------
*/

export async function compareInventory(previousFile, currentFile) {
  const formData = new FormData();

  formData.append("previous_file", previousFile);
  formData.append("current_file", currentFile);

  const response = await fetch(`${API_BASE_URL}/inventory/compare`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Compare Local Inventory
|--------------------------------------------------------------------------
*/

export async function compareLocalInventory() {
  const response = await fetch(
    `${API_BASE_URL}/inventory/compare-local`,
    {
      method: "POST",
    }
  );

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Generate Report
|--------------------------------------------------------------------------
*/

export async function generateReport() {
  const response = await fetch(
    `${API_BASE_URL}/inventory/report`,
    {
      method: "POST",
    }
  );

  return handleResponse(response);
}

/*
|--------------------------------------------------------------------------
| Download Report
|--------------------------------------------------------------------------
*/

export function getReportDownloadUrl() {
  return `${API_BASE_URL}/inventory/report/download`;
}

export default {
  checkHealth,
  getInventoryStatus,
  cleanInventory,
  compareInventory,
  compareLocalInventory,
  generateReport,
  getReportDownloadUrl,
};