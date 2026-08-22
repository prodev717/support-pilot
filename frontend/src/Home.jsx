import { RefreshCw } from "lucide-react";
import { useCache } from "./useCache";

const apiUrl = import.meta.env.VITE_API_URL ?? "";

function HealthBadge({ status }) {
  const isHealthy = status === "healthy";
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${isHealthy ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
      {status}
    </span>
  );
}

function Home() {
  const { data: tickets = [], isValidating: ticketsValidating, refresh: refreshTickets } = useCache(`${apiUrl}/tickets`);
  const { data: documents = [], isValidating: docsValidating, refresh: refreshDocuments } = useCache(`${apiUrl}/documents`);
  const { data: emails = [], isValidating: emailsValidating, refresh: refreshEmails } = useCache(`${apiUrl}/emails`);
  const { data: health, isValidating: healthValidating, refresh: refreshHealth } = useCache(`${apiUrl}/health`);

  const isSyncing = ticketsValidating || docsValidating || emailsValidating || healthValidating;

  const refreshAll = () => {
    refreshTickets();
    refreshDocuments();
    refreshEmails();
    refreshHealth();
  };

  const ticketCounts = tickets.reduce(
    (stats, item) => {
      const status = (item.ticket_status ?? "unknown").toLowerCase();
      stats[status] = (stats[status] || 0) + 1;
      return stats;
    },
    { open: 0, pending: 0, escalated: 0, closed: 0, unknown: 0 }
  );

  const healthServices = health?.services ? Object.entries(health.services) : [];

  return (
    <div className="space-y-8">
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Analytics dashboard</h1>
            <p className="mt-2 text-sm text-gray-600">
              Overview of tickets, knowledge base documents, email routing volume, and system health.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {isSyncing && (
              <span className="flex items-center gap-1.5 text-xs text-gray-500">
                <RefreshCw size={13} className="animate-spin" />
                Syncing…
              </span>
            )}
            <button
              type="button"
              onClick={refreshAll}
              disabled={isSyncing}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw size={14} className={isSyncing ? "animate-spin" : ""} />
              Refresh
            </button>
            <div className="rounded-2xl bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700">
              {isSyncing ? "Syncing…" : health?.status ? `System ${health.status}` : "Analytics ready"}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gray-500">Tickets</p>
              <p className="mt-3 text-3xl font-semibold text-gray-900">{tickets.length}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-700">
              {tickets.length ? "Live" : "Empty"}
            </div>
          </div>
          <div className="mt-6 grid gap-3 text-sm text-gray-600">
            <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-4 py-3">
              <span>Open</span>
              <span>{ticketCounts.open}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-4 py-3">
              <span>Pending</span>
              <span>{ticketCounts.pending}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-4 py-3">
              <span>Escalated</span>
              <span>{ticketCounts.escalated}</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-4 py-3">
              <span>Closed</span>
              <span>{ticketCounts.closed}</span>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gray-500">Knowledge Base</p>
              <p className="mt-3 text-3xl font-semibold text-gray-900">{documents.length}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-700">Documents</div>
          </div>
          <div className="mt-6 text-sm text-gray-600">
            <p>{documents.length === 0 ? "No documents available." : "All uploaded documents are indexed."}</p>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gray-500">Email routing</p>
              <p className="mt-3 text-3xl font-semibold text-gray-900">{emails.length}</p>
            </div>
            <div className="rounded-2xl bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-700">Routes</div>
          </div>
          <div className="mt-6 text-sm text-gray-600">
            <p>{emails.length === 0 ? "No email routes configured." : "Email routes are ready to route incoming messages."}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gray-500">Health check</p>
            <h2 className="mt-3 text-2xl font-semibold text-gray-900">{health?.status ? health.status.toUpperCase() : "Loading status"}</h2>
          </div>
          <HealthBadge status={health?.status ?? "unknown"} />
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {healthServices.length ? (
            healthServices.map(([service, status]) => (
              <div key={service} className="rounded-lg border bg-gray-50 px-5 py-4">
                <p className="text-sm font-semibold text-gray-700">{service.replace(/_/g, " ")}</p>
                <div className="mt-2 flex items-center justify-between gap-4">
                  <span className="text-sm text-gray-600">Status</span>
                  <HealthBadge status={status?.status ?? "unknown"} />
                </div>
                {status?.detail && <p className="mt-3 text-xs text-gray-500">{status.detail}</p>}
              </div>
            ))
          ) : (
            <div className="rounded-lg border bg-gray-50 px-5 py-4 text-sm text-gray-600">
              Health data is not available yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Home;
