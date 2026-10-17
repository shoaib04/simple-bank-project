export async function getMiniStatement(accountNumber) {
  const path = `/api/v1/accounts/${encodeURIComponent(accountNumber)}/mini-statement`;
  let response;
  try {
    response = await fetch(path, {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
  } catch (cause) {
    const error = new Error("Unable to connect. Try again.", { cause });
    error.code = "NETWORK_ERROR";
    throw error;
  }

  let result;
  try {
    result = await response.json();
  } catch (cause) {
    const error = new Error("The statement response was invalid.", { cause });
    error.code = "INVALID_RESPONSE";
    error.status = response.status;
    throw error;
  }

  if (!response.ok) {
    const error = new Error(result.message ?? "The statement is unavailable.");
    error.code = result.code ?? "INVALID_REQUEST";
    error.status = response.status;
    throw error;
  }

  return result;
}
