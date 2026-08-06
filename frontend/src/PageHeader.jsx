import { NavLink } from "react-router";

const PageHeader = () => {
  return (
    <header className="w-full bg-white border-b border-black">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <NavLink to="/">
          <h1 className="text-3xl font-bold text-black">
            Support Pilot
          </h1>
        </NavLink>

        <p className="mt-2 text-gray-600">
          AI-Powered Customer Support Retrieval &amp; Inbox Management Workspace
        </p>
      </div>
    </header>
  );
};

export default PageHeader;