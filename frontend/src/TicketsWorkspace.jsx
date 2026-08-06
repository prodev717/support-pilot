import { useState, useEffect } from "react";

function TicketsWorkspace() {
  const apiUrl = import.meta.env.VITE_API_URL;

  const [tickets, setTickets] = useState([]);
  const [ticket, setTicket] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [error, setError] = useState(null);
  const [draftReply, setDraftReply] = useState("");
  const [sending, setSending] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const [updateSuccessMessage, setUpdateSuccessMessage] = useState(null);
  const [deleteSuccessMessage, setDeleteSuccessMessage] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [actionStatus, setActionStatus] = useState("");
  const [actionSeverity, setActionSeverity] = useState("");
  const [actionForwardedTo, setActionForwardedTo] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newTicketCustomerEmail, setNewTicketCustomerEmail] = useState("");
  const [newTicketSubject, setNewTicketSubject] = useState("");
  const [newTicketBody, setNewTicketBody] = useState("");
  const [newTicketIssue, setNewTicketIssue] = useState("");
  const [newTicketSeverity, setNewTicketSeverity] = useState("medium");
  const [newTicketStatus, setNewTicketStatus] = useState("Open");
  const [newTicketAssignedTo, setNewTicketAssignedTo] = useState("");
  const [createTicketError, setCreateTicketError] = useState(null);
  const [createTicketSuccessMessage, setCreateTicketSuccessMessage] = useState(null);

  const fetchTickets = async (statusFilter = filterStatus) => {
    try {
      const url = statusFilter
        ? `${apiUrl}/tickets?status=${encodeURIComponent(statusFilter)}`
        : `${apiUrl}/tickets`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to load tickets: ${response.status}`);
      }

      const data = await response.json();
      setTickets(data);

      if (Array.isArray(data) && data.length) {
        setSelectedTicket((current) => {
          if (current && data.some((item) => item.ticket_id === current)) {
            return current;
          }
          return data[0].ticket_id;
        });
      } else {
        setSelectedTicket(null);
      }
    } catch (fetchError) {
      console.error(fetchError);
      setError("Unable to load tickets. Please refresh the page.");
    }
  };

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const response = await fetch(`${apiUrl}/emails`);
        if (!response.ok) {
          throw new Error(`Failed to load departments: ${response.status}`);
        }
        const data = await response.json();
        setDepartments(data);
      } catch (fetchError) {
        console.error(fetchError);
      }
    };

    fetchDepartments();
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [filterStatus]);

  useEffect(() => {
    if (!selectedTicket) {
      return;
    }

    const fetchTicket = async () => {
      try {
        const response = await fetch(`${apiUrl}/tickets/${selectedTicket}`);

        if (!response.ok) {
          throw new Error(`Failed to load ticket: ${response.status}`);
        }

        const data = await response.json();
        setTicket(data);
        console.log("Selected Ticket Data:", data);
      } catch (fetchError) {
        console.error(fetchError);
        setError("Unable to load the selected ticket. Please try again.");
      }
    };

    fetchTicket();
  }, [selectedTicket]);

  useEffect(() => {
    if (!ticket) {
      setDraftReply("");
      setActionStatus("");
      setActionSeverity("");
      setActionForwardedTo("");
      setSuccessMessage(null);
      setUpdateSuccessMessage(null);
      setDeleteSuccessMessage(null);
      return;
    }

    setDraftReply(ticket.ai_draft_reply ?? "");
    setActionStatus(ticket.ticket_status ?? "");
    setActionSeverity(ticket.severity ?? "");
    setActionForwardedTo(ticket.forwarded_to ?? "");
    setSuccessMessage(null);
    setUpdateSuccessMessage(null);
    setDeleteSuccessMessage(null);
  }, [ticket]);

  const sendDraftReply = async () => {
    if (!ticket) {
      return;
    }

    setSending(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`${apiUrl}/tickets/${ticket.ticket_id}/send-draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft_reply: draftReply }),
      });

      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || response.statusText || `Status ${response.status}`);
      }

      const result = await response.json().catch(() => null);
      setSuccessMessage(result?.message || "Reply sent successfully.");
      setTicket((current) =>
        current
          ? {
              ...current,
              ticket_status: "Closed",
              ai_draft_reply: null,
            }
          : current
      );
      setTickets((current) =>
        current.map((item) =>
          item.ticket_id === ticket.ticket_id ? { ...item, ticket_status: "Closed" } : item
        )
      );
      setDraftReply("");
    } catch (sendError) {
      console.error(sendError);
      setError(`Unable to send reply: ${sendError.message}`);
    } finally {
      setSending(false);
    }
  };

  const updateTicket = async () => {
    if (!ticket) {
      return;
    }

    setUpdating(true);
    setError(null);
    setSuccessMessage(null);
    setDeleteSuccessMessage(null);
    setUpdateSuccessMessage(null);

    try {
      const response = await fetch(`${apiUrl}/tickets/${ticket.ticket_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_status: actionStatus || null,
          severity: actionSeverity || null,
          forwarded_to: actionForwardedTo || null,
        }),
      });

      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || response.statusText || `Status ${response.status}`);
      }

      const result = await response.json().catch(() => null);
      setUpdateSuccessMessage(result?.status === "success" ? "Ticket updated successfully." : "Ticket updated successfully.");

      const updatedTicket = {
        ...ticket,
        ticket_status: actionStatus,
        severity: actionSeverity,
        forwarded_to: actionForwardedTo,
      };
      setTicket(updatedTicket);
      setTickets((current) =>
        current.map((item) =>
          item.ticket_id === ticket.ticket_id
            ? { ...item, ticket_status: actionStatus }
            : item
        )
      );
    } catch (updateError) {
      console.error(updateError);
      setError(`Unable to update ticket: ${updateError.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const deleteTicket = async () => {
    if (!ticket) {
      return;
    }

    setDeleting(true);
    setError(null);
    setDeleteSuccessMessage(null);

    try {
      const response = await fetch(`${apiUrl}/tickets/${ticket.ticket_id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || response.statusText || `Status ${response.status}`);
      }

      await response.json().catch(() => null);
      setDeleteSuccessMessage(`Ticket #${ticket.ticket_id} deleted successfully.`);
      setTickets((current) => current.filter((item) => item.ticket_id !== ticket.ticket_id));
      setTicket(null);
      setSelectedTicket(null);
    } catch (deleteError) {
      console.error(deleteError);
      setError(`Unable to delete ticket: ${deleteError.message}`);
    } finally {
      setDeleting(false);
    }
  };

  const createTicket = async () => {
    setCreateTicketError(null);
    setCreateTicketSuccessMessage(null);

    if (!newTicketCustomerEmail.trim()) {
      setCreateTicketError("Customer email is required.");
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_email: newTicketCustomerEmail,
          subject: newTicketSubject || null,
          body: newTicketBody || null,
          issue: newTicketIssue || null,
          severity: newTicketSeverity || null,
          ticket_status: newTicketStatus || null,
          forwarded_to: newTicketAssignedTo || null,
        }),
      });

      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || response.statusText || `Status ${response.status}`);
      }

      const result = await response.json();
      if (result.status !== "success") {
        throw new Error("Unable to create ticket.");
      }

      setCreateTicketSuccessMessage(`Ticket #${result.ticket.ticket_id} created successfully.`);
      setIsCreateModalOpen(false);
      setNewTicketCustomerEmail("");
      setNewTicketSubject("");
      setNewTicketBody("");
      setNewTicketIssue("");
      setNewTicketSeverity("medium");
      setNewTicketStatus("Open");
      setNewTicketAssignedTo("");
      await fetchTickets();
      setSelectedTicket(result.ticket.ticket_id);
    } catch (createError) {
      console.error(createError);
      setCreateTicketError(`Unable to create ticket: ${createError.message}`);
    }
  };

  const statusColor = {
    Closed: "bg-green-100 text-green-700",
    Pending: "bg-yellow-100 text-yellow-700",
    Escalated: "bg-red-100 text-red-700",
    Open: "bg-blue-100 text-blue-700",
  };

  return (
    <>
      <div className="flex flex-col gap-4 px-4">
        <div>
          <h1 className="text-2xl font-semibold">Tickets Workspace</h1>
          <p className="text-sm text-gray-500">
            View, route, and manage incoming support tickets with status, severity, and assignment controls.
          </p>
        </div>
      </div>

      <div className="h-[calc(100vh-81px)] p-4">
        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
            {error}
          </div>
        ) : (
          <div className="grid h-full min-h-0 overflow-hidden rounded-lg border bg-white lg:grid-cols-3">
          {/* LEFT PANEL */}
          <aside className="grid min-h-0 grid-rows-[auto_1fr] border-r">
            {/* Header */}
            <div className="border-b bg-white p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Tickets</h2>
                  <p className="text-sm text-gray-500">
                    {tickets.length} ticket{tickets.length !== 1 && "s"}
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <select
                    value={filterStatus}
                    onChange={(event) => setFilterStatus(event.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  >
                    <option value="">All statuses</option>
                    <option value="Open">Open</option>
                    <option value="Pending">Pending</option>
                    <option value="Escalated">Escalated</option>
                    <option value="Closed">Closed</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(true)}
                    className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black"
                  >
                    Add Ticket
                  </button>
                </div>
              </div>
            </div>

            {/* Scrollable List */}
            <div className="min-h-0 overflow-y-auto scrollbar-none">
              {tickets.map((ticket) => (
                <button
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket.ticket_id)}
                  className={`w-full border-b p-4 text-left transition-colors hover:bg-gray-50 ${selectedTicket === ticket.ticket_id
                    ? "bg-gray-100"
                    : "bg-white"
                    }`}
                >
                  {/* Subject + Time */}
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="flex-1 truncate font-medium text-gray-900">
                      {ticket.ticket_id}:{ticket.subject}
                    </h3>

                    <span className="shrink-0 text-xs text-gray-500">
                      {new Intl.DateTimeFormat(navigator.language, {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(ticket.updated_at))}
                    </span>
                  </div>

                  {/* Customer */}
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {ticket.customer_email}
                  </p>

                  {/* Footer */}
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      {ticket.severity}
                    </span>

                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${statusColor[ticket.ticket_status]
                          }`}
                      >
                        {ticket.ticket_status}
                      </span>

                      <span className="text-xs text-gray-500">
                        {ticket.message_count} message
                        {ticket.message_count !== 1 && "s"}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </aside>
          {/* RIGHT PANEL */}
          <section className="min-h-0 overflow-y-auto bg-gray-50 lg:col-span-2">
            {ticket && (
              <div className="flex h-full flex-col">
                {/* Header */}
                <div className="border-b bg-white p-6">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h2 className="text-2xl font-semibold text-gray-900">
                        {ticket.subject}
                      </h2>

                      <p className="mt-1 text-sm text-gray-500">
                        Ticket #{ticket.ticket_id}, From: {ticket.customer_email}
                      </p>
                    </div>

                    <span
                      className={`self-start rounded-full px-3 py-1 text-sm font-medium ${statusColor[ticket.ticket_status]
                        }`}
                    >
                      {ticket.ticket_status}
                    </span>
                  </div>
                </div>

                {/* Body */}
                <div className="flex-1 space-y-6 overflow-y-auto p-6">
                  {/* Metadata */}
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

                    <div className="rounded-lg border bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500">
                        Issue
                      </p>
                      <p className="mt-1 font-medium capitalize">{ticket.issue}</p>
                    </div>

                    <div className="rounded-lg border bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500">
                        Severity
                      </p>
                      <p className="mt-1 font-medium capitalize">{ticket.severity}</p>
                    </div>

                    <div className="rounded-lg border bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500">
                        Sentiment
                      </p>
                      <p className="mt-1 capitalize font-medium">
                        {ticket.sentiment} • {ticket.emotion}
                      </p>
                    </div>
                  </div>

                  {/* AI Analysis */}
                  <div className="grid gap-6 xl:grid-cols-2">
                    <div className="rounded-lg border bg-white p-5">
                      <h3 className="mb-3 text-lg font-semibold">
                        AI Decision
                      </h3>

                      <p className="whitespace-pre-wrap text-sm leading-7 text-gray-700">
                        {ticket.ai_decision}
                      </p>
                    </div>

                    <div className="rounded-lg border bg-white p-5">
                      <h3 className="mb-3 text-lg font-semibold">
                        Suggested Reply
                      </h3>

                      <div className="mt-3">
                        <textarea
                          value={draftReply}
                          onChange={(event) => setDraftReply(event.target.value)}
                          placeholder="Edit the AI suggested reply before sending it to the customer."
                          rows={10}
                          className="min-h-[12rem] w-full resize-none rounded-md border border-black bg-white p-3 text-sm text-black"
                        />
                      </div>

                      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <button
                          type="button"
                          onClick={sendDraftReply}
                          disabled={sending || !draftReply.trim()}
                          className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                        >
                          {sending ? "Sending..." : "Send Reply"}
                        </button>

                        {successMessage && (
                          <p className="text-sm text-green-700">{successMessage}</p>
                        )}
                      </div>

                      {!ticket.ai_draft_reply && (
                        <p className="mt-3 text-sm text-gray-500">
                          No suggested AI reply is available. Enter a reply above to send to the customer.
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-lg border bg-white p-5">
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <h3 className="mb-1 text-lg font-semibold">Actions & Routing</h3>
                        <p className="text-sm text-gray-500">Update status, severity, and assigned department for this ticket.</p>
                      </div>
                      <button
                        type="button"
                        onClick={updateTicket}
                        disabled={updating}
                        className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                      >
                        {updating ? "Saving..." : "Save changes"}
                      </button>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-3">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700">Status</label>
                        <select
                          value={actionStatus}
                          onChange={(event) => setActionStatus(event.target.value)}
                          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                        >
                          <option value="">Select status</option>
                          <option value="Open">Open</option>
                          <option value="Pending">Pending</option>
                          <option value="Escalated">Escalated</option>
                          <option value="Closed">Closed</option>
                        </select>
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700">Severity</label>
                        <select
                          value={actionSeverity}
                          onChange={(event) => setActionSeverity(event.target.value)}
                          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                        >
                          <option value="">Select severity</option>
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700">Assigned Department</label>
                        <select
                          value={actionForwardedTo}
                          onChange={(event) => setActionForwardedTo(event.target.value)}
                          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                        >
                          <option value="">Unassigned</option>
                          {departments.map((department) => (
                            <option key={department.id} value={department.email}>
                              {department.department}{department.email ? ` — ${department.email}` : ""}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {updateSuccessMessage && (
                      <p className="mt-4 text-sm text-green-700">{updateSuccessMessage}</p>
                    )}
                  </div>

                  {/* Conversation */}
                  <div className="rounded-lg border bg-white">
                    <div className="border-b p-5">
                      <h3 className="text-lg font-semibold">
                        Conversation
                      </h3>

                      <p className="text-sm text-gray-500">
                        {(ticket.messages ?? []).length} message
                        {(ticket.messages ?? []).length !== 1 && "s"}
                      </p>
                    </div>

                    <div className="divide-y">
                      {[...(ticket.messages ?? [])]
                        .sort(
                          (a, b) =>
                            new Date(a.created_at) - new Date(b.created_at)
                        )
                        .map((message, index) => (
                          <div
                            key={message.id}
                            className="space-y-4 p-5"
                          >
                            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                              <div>
                                <h4 className="font-semibold text-gray-900">
                                  Message {index + 1}
                                </h4>

                                <p className="text-sm text-gray-600">
                                  {message.subject}
                                </p>
                              </div>

                              <span className="text-xs text-gray-500">
                                {new Intl.DateTimeFormat(navigator.language, {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                }).format(new Date(message.created_at))}
                              </span>
                            </div>

                            <div className="rounded-md bg-gray-50 p-4">
                              <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-gray-700">
                                {message.body}
                              </pre>
                            </div>

                            <div className="flex flex-wrap gap-2 text-xs">
                              <span className="rounded-full bg-gray-100 px-3 py-1">
                                Issue: {message.issue}
                              </span>

                              <span className="rounded-full bg-gray-100 px-3 py-1">
                                Severity: {message.severity}
                              </span>

                              <span className="rounded-full bg-gray-100 px-3 py-1">
                                Sentiment: {message.sentiment}
                              </span>

                              <span className="rounded-full bg-gray-100 px-3 py-1">
                                Emotion: {message.emotion}
                              </span>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>

                  <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <button
                      type="button"
                      onClick={deleteTicket}
                      disabled={deleting}
                      className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                    >
                      {deleting ? "Deleting..." : "Delete Ticket"}
                    </button>

                    {deleteSuccessMessage && (
                      <p className="text-sm text-green-700">{deleteSuccessMessage}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">Create Ticket</h2>
                <p className="text-sm text-gray-500">Add a manual ticket for a customer request.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-700">Customer Email</label>
                <input
                  value={newTicketCustomerEmail}
                  onChange={(event) => setNewTicketCustomerEmail(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="customer@example.com"
                />
              </div>

              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-700">Subject</label>
                <input
                  value={newTicketSubject}
                  onChange={(event) => setNewTicketSubject(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Issue subject"
                />
              </div>

              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-700">Body</label>
                <textarea
                  value={newTicketBody}
                  onChange={(event) => setNewTicketBody(event.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Ticket description"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">Issue</label>
                <input
                  value={newTicketIssue}
                  onChange={(event) => setNewTicketIssue(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                  placeholder="Billing, support, etc."
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">Status</label>
                <select
                  value={newTicketStatus}
                  onChange={(event) => setNewTicketStatus(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                >
                  <option value="Open">Open</option>
                  <option value="Pending">Pending</option>
                  <option value="Escalated">Escalated</option>
                  <option value="Closed">Closed</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">Severity</label>
                <select
                  value={newTicketSeverity}
                  onChange={(event) => setNewTicketSeverity(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-700">Assigned Department</label>
                <select
                  value={newTicketAssignedTo}
                  onChange={(event) => setNewTicketAssignedTo(event.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                >
                  <option value="">Unassigned</option>
                  {departments.map((department) => (
                    <option key={department.id} value={department.email}>
                      {department.department}{department.email ? ` — ${department.email}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {createTicketError && (
              <p className="mt-4 text-sm text-red-700">{createTicketError}</p>
            )}
            {createTicketSuccessMessage && (
              <p className="mt-4 text-sm text-green-700">{createTicketSuccessMessage}</p>
            )}

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={createTicket}
                className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black"
              >
                Create Ticket
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </>
  );
}

export default TicketsWorkspace;
