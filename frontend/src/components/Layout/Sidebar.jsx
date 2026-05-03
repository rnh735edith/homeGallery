import { NavLink } from "react-router-dom";

const navItems = [
  { path: "/", label: "Gallery", icon: "\u{1F5BC}" },
  { path: "/albums", label: "Albums", icon: "\u{1F4C1}" },
  { path: "/duplicates", label: "Duplicates", icon: "\u{1F517}" },
  { path: "/faces", label: "Faces", icon: "\u{1F464}" },
  { path: "/dashboard", label: "Dashboard", icon: "\u{1F4CA}" },
  { path: "/settings", label: "Settings", icon: "\u2699" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>HomeGallery</h1>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
            end={item.path === "/"}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span className="sidebar-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
