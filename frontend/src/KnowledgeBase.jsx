import { useEffect, useState } from "react";

function KnowledgeBase() {
  const apiUrl = import.meta.env.VITE_API_URL;

  const [documents, setDocuments] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [documentFile, setDocumentFile] = useState(null);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(200);
  const [uploading, setUploading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState(null);
  const [searchMessage, setSearchMessage] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadDocuments = async () => {
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/documents`);
      if (!response.ok) {
        throw new Error(`Failed to load documents: ${response.status}`);
      }
      const data = await response.json();
      setDocuments(data);
    } catch (loadError) {
      console.error(loadError);
      setError("Unable to load documents. Please refresh the page.");
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [refreshKey]);

  const handleUpload = async () => {
    setError(null);
    setUploadSuccessMessage(null);
    if (!documentFile) {
      setError("Please select a document to upload.");
      return;
    }

    const formData = new FormData();
    formData.append("file", documentFile);
    formData.append("chunk_size", String(chunkSize));
    formData.append("overlap", String(overlap));

    setUploading(true);
    try {
      const response = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }

      const result = await response.json();
      setUploadSuccessMessage(`Uploaded ${result.filename} with ${result.chunks} chunks.`);
      setDocumentFile(null);
      setSearchResults([]);
      setSearchMessage(null);
      setRefreshKey((current) => current + 1);
    } catch (uploadError) {
      console.error(uploadError);
      setError(`Upload failed: ${uploadError.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async () => {
    setError(null);
    setSearchMessage(null);
    if (!searchQuery.trim()) {
      setError("Enter a query to search the knowledge base.");
      return;
    }

    setSearching(true);
    try {
      const response = await fetch(
        `${apiUrl}/search?query=${encodeURIComponent(searchQuery)}&top_k=${encodeURIComponent(topK)}`
      );
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }

      const result = await response.json();
      setSearchResults(result.results || []);
      setSearchMessage(`Showing top ${result.results?.length ?? 0} results for "${result.query}".`);
    } catch (searchError) {
      console.error(searchError);
      setError(`Search failed: ${searchError.message}`);
    } finally {
      setSearching(false);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    setError(null);
    setDeletingId(documentId);
    try {
      const response = await fetch(`${apiUrl}/documents/${encodeURIComponent(documentId)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const result = await response.json().catch(() => null);
        throw new Error(result?.detail || `Status ${response.status}`);
      }
      setRefreshKey((current) => current + 1);
    } catch (deleteError) {
      console.error(deleteError);
      setError(`Unable to delete document: ${deleteError.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge Base</h1>
          <p className="text-sm text-gray-500">Upload content, query the index, and manage documents.</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {uploadSuccessMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">{uploadSuccessMessage}</div>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-lg border bg-white p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Upload Document</h2>
              <p className="text-sm text-gray-500">Upload a PDF, DOCX or TXT file for chunking.</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">File</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(event) => setDocumentFile(event.target.files?.[0] ?? null)}
                className="mt-2 block w-full text-sm text-gray-700"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Chunk size</span>
                <input
                  type="number"
                  min={1}
                  value={chunkSize}
                  onChange={(event) => setChunkSize(Number(event.target.value))}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Overlap</span>
                <input
                  type="number"
                  min={0}
                  value={overlap}
                  onChange={(event) => setOverlap(Number(event.target.value))}
                  className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                />
              </label>
            </div>

            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading}
              className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
            >
              {uploading ? "Uploading..." : "Upload document"}
            </button>
          </div>
        </section>

        <section className="rounded-lg border bg-white p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Search</h2>
              <p className="text-sm text-gray-500">Search your document chunks with the vector index.</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700">Query</span>
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                placeholder="Search the knowledge base"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-gray-700">Top K</span>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(event) => setTopK(Number(event.target.value))}
                className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
              />
            </label>

            <button
              type="button"
              onClick={handleSearch}
              disabled={searching}
              className="inline-flex items-center justify-center rounded-md border border-black bg-black px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
            >
              {searching ? "Searching..." : "Search knowledge base"}
            </button>

            {searchMessage && (
              <p className="text-sm text-gray-600">{searchMessage}</p>
            )}
          </div>
        </section>
      </div>

      <section className="rounded-lg border bg-white p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Documents</h2>
            <p className="text-sm text-gray-500">Uploaded documents stored in the knowledge base.</p>
          </div>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
            {documents.length} document{documents.length !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="mt-6 space-y-3">
          {documents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5 text-sm text-gray-500">
              No documents uploaded yet.
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.document_id} className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-gray-900">{doc.filename}</p>
                  <p className="text-sm text-gray-500">{doc.chunks} chunks</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteDocument(doc.document_id)}
                  disabled={deletingId === doc.document_id}
                  className="inline-flex items-center justify-center rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                >
                  {deletingId === doc.document_id ? "Deleting..." : "Delete"}
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      {searchResults.length > 0 && (
        <section className="rounded-lg border bg-white p-6">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Search Results</h2>
              <p className="text-sm text-gray-500">Relevant chunks from the uploaded documents.</p>
            </div>
          </div>

          <div className="space-y-4">
            {searchResults.map((result, index) => (
              <div key={`${result.document_id}-${result.chunk_id}-${index}`} className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="font-medium text-gray-900">{result.filename}</p>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-500">
                    Chunk {result.chunk_id} • {result.score?.toFixed(2)}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-gray-700 whitespace-pre-wrap">{result.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default KnowledgeBase;
