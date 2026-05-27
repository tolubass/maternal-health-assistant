import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  const linkClass = ({ isActive }) =>
    isActive ? 'nav-link nav-link--active' : 'nav-link';

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand" onClick={close}>
          <span className="navbar-brand-icon" aria-hidden="true">🩺</span>
          <div>
            <span className="navbar-title">Maternal Health Assistant</span>
            <span className="navbar-subtitle">Nigeria · WHO &amp; FMOH Guidelines</span>
          </div>
        </Link>

        <button
          className={`menu-toggle${open ? ' menu-toggle--open' : ''}`}
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(v => !v)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav
          className={`navbar-nav${open ? ' navbar-nav--open' : ''}`}
          aria-label="Main navigation"
        >
          <NavLink to="/" end className={linkClass} onClick={close}>Home</NavLink>
          <NavLink to="/chat" className={linkClass} onClick={close}>Chat</NavLink>
          <NavLink to="/faq" className={linkClass} onClick={close}>FAQ</NavLink>
          <Link to="/chat" className="nav-cta" onClick={close}>Ask a Question</Link>
        </nav>
      </div>
    </header>
  );
}
