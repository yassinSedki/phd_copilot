import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/opportunities", label: "Opportunities" },
  { to: "/tracker", label: "Tracker" },
  { to: "/deepdive", label: "Deep-dive" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const { email, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6">
          <div className="font-semibold text-lg text-brand-700">phd-copilot</div>
          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm ${
                    isActive
                      ? "bg-brand-50 text-brand-700 font-medium"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-slate-500">{email}</span>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="btn-ghost"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
