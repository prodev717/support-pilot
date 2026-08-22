import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useCache } from "./useCache";

function EmailRouting() {
  const apiUrl = import.meta.env.VITE_API_URL;

  const { data: emails = [], isValidating, refresh, mutate } = useCache(`${apiUrl}/emails`);

  const [selectedEmail, setSelectedEmail] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const [department, setDepartment] = useState("");
  const [email, setEmail] = useState("");
  const [description, setDescription] = useState("");

  const [newDepartment, setNewDepartment] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newError, setNewError] = useState(null);

  // Auto-select first route when data loads
  useEffect(() => {
    if (emails.length && !selectedEmail) {
      setSelectedEmail(emails[0].id);
    }
  }, [emails]);

  // Populate edit form when selection changes
  useEffect(() => {
    if (!selectedEmail) {
      setDepartment("");
      setEmail("");
      setDescription("");
      return;
    }
    const route = emails.find((item) => item.id === selectedEmail);
    if (route) {
      setDepartment(route.department || "");
      setEmail(route.email || "");
      setDescription(route.description || "");
    }
  }, [selectedEmail, emails]);

  const saveEmailRoute = async () => {
    if (!selectedEmail) return;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await fetch(`${apiUrl}/emails/${selectedEmail}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          department: department || null,
          email: email || null,
          description: description || null,
        }),
      });
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }
      const result = await response.json();
      if (result.status !== "success") throw new Error("Unable to save route.");
      setSuccessMessage("Email routing updated successfully.");
      mutate();
    } catch (saveError) {
      console.error(saveError);
      setError(`Unable to save route: ${saveError.message}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteEmailRoute = async () => {
    if (!selectedEmail) return;
    setDeleting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await fetch(`${apiUrl}/emails/${selectedEmail}`, { method: "DELETE" });
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }
      await response.json().catch(() => null);
      setSuccessMessage("Email routing deleted successfully.");
      setSelectedEmail(null);
      mutate();
    } catch (deleteError) {
      console.error(deleteError);
      setError(`Unable to delete route: ${deleteError.message}`);
    } finally {
      setDeleting(false);
    }
  };

  const createEmailRoute = async () => {
    setNewError(null);
    if (!newDepartment.trim() || !newEmail.trim()) {
      setNewError("Department and email are required.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await fetch(`${apiUrl}/emails`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          department: newDepartment,
          email: newEmail,
          description: newDescription || null,
        }),
      });
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }
      const result = await response.json();
      if (result.status !== "success") throw new Error("Unable to create route.");
      setSuccessMessage("Email routing created successfully.");
      setCreateModalOpen(false);
      setNewDepartment("");
      setNewEmail("");
      setNewDescription("");
      await mutate();
      setSelectedEmail(result.email.id);
    } catch (createError) {
      console.error(createError);
      setNewError(`Unable to create route: ${createError.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Email Routing</h1>
          <p className="text-sm text-gray-500">Manage department routing addresses and descriptions.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={refresh}
            disabled={isValidating}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isValidating ? "animate-spin" : ""} />
            {isValidating ? "Syncing…" : "Refresh"}
          </button>
          <button
            type="button"
            onClick={() => setCreateModalOpen(true)}
            className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black"
          >
            Add Route
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {successMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">{successMessage}</div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <aside className="rounded-lg border bg-white p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Routes</h2>
            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              {emails.length}
            </span>
          </div>

          <div className="space-y-2">
            {isValidating && emails.length === 0 ? (
              <div className="text-sm text-gray-500">Loading routes...</div>
            ) : emails.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500">
                No routing rules defined.
              </div>
            ) : (
              emails.map((route) => (
                <button
                  key={route.id}
                  type="button"
                  onClick={() => setSelectedEmail(route.id)}
                  className={`w-full rounded-xl border px-4 py-4 text-left transition ${selectedEmail === route.id ? "border-black bg-gray-50" : "border-gray-200 bg-white hover:bg-gray-50"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-gray-900">{route.department}</p>
                    <span className="text-xs text-gray-500">ID {route.id}</span>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{route.email}</p>
                  <p className="mt-2 text-xs text-gray-500">{route.description || "No description"}</p>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="lg:col-span-2 rounded-lg border bg-white p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Route details</h2>
              <p className="text-sm text-gray-500">Edit or delete the selected route.</p>
            </div>
          </div>

          {!selectedEmail ? (
            <div className="mt-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-500">
              Select a route to edit its details.
            </div>
          ) : (
            <div className="mt-6 space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Department</span>
                  <input
                    value={department}
                    onChange={(event) => setDepartment(event.target.value)}
                    className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                    placeholder="Billing"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Email address</span>
                  <input
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                    placeholder="billing@example.com"
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-sm font-medium text-gray-700">Description</span>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={4}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Optional route description"
                />
              </label>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={saveEmailRoute}
                    disabled={saving}
                    className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                  >
                    {saving ? "Saving..." : "Save changes"}
                  </button>
                  <button
                    type="button"
                    onClick={deleteEmailRoute}
                    disabled={deleting}
                    className="inline-flex items-center justify-center rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                  >
                    {deleting ? "Deleting..." : "Delete route"}
                  </button>
                </div>
                {successMessage && <p className="text-sm text-green-700">{successMessage}</p>}
              </div>
            </div>
          )}
        </section>
      </div>

      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">New email route</h2>
                <p className="text-sm text-gray-500">Create a new department routing email.</p>
              </div>
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <label className="block md:col-span-2">
                <span className="text-sm font-medium text-gray-700">Department</span>
                <input
                  value={newDepartment}
                  onChange={(event) => setNewDepartment(event.target.value)}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Billing"
                />
              </label>

              <label className="block md:col-span-2">
                <span className="text-sm font-medium text-gray-700">Email address</span>
                <input
                  value={newEmail}
                  onChange={(event) => setNewEmail(event.target.value)}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="billing@example.com"
                />
              </label>

              <label className="block md:col-span-2">
                <span className="text-sm font-medium text-gray-700">Description</span>
                <textarea
                  value={newDescription}
                  onChange={(event) => setNewDescription(event.target.value)}
                  rows={4}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Optional description"
                />
              </label>
            </div>

            {newError && <p className="mt-4 text-sm text-red-700">{newError}</p>}

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={createEmailRoute}
                className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black"
              >
                Create route
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EmailRouting;
