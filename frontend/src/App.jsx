import { BrowserRouter, Routes, Route } from "react-router";
import PageHeader from "./PageHeader.jsx";
import Sidebar from "./Sidebar.jsx";
import TicketsWorkspace from "./TicketsWorkspace.jsx";
import KnowledgeBase from "./KnowledgeBase.jsx";
import EmailRouting from "./EmailRouting.jsx";
import Home from "./Home.jsx";

function App() {
  return (
    <BrowserRouter>
      <Sidebar />

      <div className="min-h-screen bg-slate-50 md:pl-64">
        <PageHeader />

        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/tickets" element={<TicketsWorkspace />} />
            <Route path="/knowledge-base" element={<KnowledgeBase />} />
            <Route path="/email-routing" element={<EmailRouting />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
