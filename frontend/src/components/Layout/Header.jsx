import { useAuthStore } from '../../store/authStore'

export default function Header() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <header className="header">
      <div className="header-right">
        {user && <span className="header-user">{user.username}</span>}
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  )
}
