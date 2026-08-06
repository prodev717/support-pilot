import { NavLink } from "react-router";
import { Menu, X } from "lucide-react";
import { useState } from "react";

const links = [
  { name: "Tickets Workspace", path: "/tickets" },
  { name: "Knowledge Base", path: "/knowledge-base" },
  { name: "Email Routing", path: "/email-routing" },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile Header */}
      <div className="flex items-center justify-between border-b bg-white p-4 md:hidden">
        <h2 className="text-lg font-semibold">Menu</h2>

        <button onClick={() => setOpen(!open)}>
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-40 h-screen w-64 border-r bg-white transform transition-transform duration-300
        ${open ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0`}
      >
        <div className="border-b p-6">
          <NavLink to="/">
            <h1 className="text-xl font-bold">Support Pilot</h1>
          </NavLink>
        </div>

        <nav className="flex flex-col p-4 gap-2">
          {links.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `rounded-lg px-4 py-2 transition ${
                  isActive
                    ? "bg-black text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`
              }
            >
              {link.name}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}