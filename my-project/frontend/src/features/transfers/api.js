export async function createTransfer(request) {
  const response = await fetch("/api/v1/transfers", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const result = await response.json();

  if (!response.ok) {
    const error = new Error(result.message ?? "The transfer request could not be completed.");
    error.code = result.code ?? "INVALID_REQUEST";
    error.status = response.status;
    throw error;
  }

  return result;
}
