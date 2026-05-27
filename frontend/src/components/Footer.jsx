import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span aria-hidden="true">🩺</span>
          <span className="footer-brand-name">Maternal Health Assistant</span>
        </div>

        <nav className="footer-nav" aria-label="Footer links">
          <Link to="/">Home</Link>
          <Link to="/chat">Chat</Link>
          <Link to="/faq">FAQ</Link>
        </nav>

        <p className="footer-disclaimer">
          For emergencies call <strong>112</strong>. This assistant does not
          replace professional medical advice — always consult a qualified health worker.
        </p>

        <p className="footer-copy">
          &copy; {new Date().getFullYear()} Maternal Health Assistant &middot; Abuja, Nigeria
        </p>
      </div>
    </footer>
  );
}
