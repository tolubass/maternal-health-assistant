import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const FEATURES = [
  {
    icon: '📋',
    title: 'Evidence-Based Answers',
    desc: 'Every response is grounded in WHO guidelines, Nigerian Federal Ministry of Health protocols, NPHCDA standards, and UNICEF maternal health resources.',
  },
  {
    icon: '🛡️',
    title: 'Built-In Safety Stack',
    desc: 'A four-layer safety system detects emergencies, blocks unsafe advice, validates every response, and routes you to care when a question is life-threatening.',
  },
  {
    icon: '🌍',
    title: 'Nigeria-Focused Context',
    desc: 'Answers are tailored to the Nigerian healthcare system — including local emergency numbers, national immunisation schedules, and FMOH policies.',
  },
  {
    icon: '💬',
    title: 'Plain Language',
    desc: 'Get clear, jargon-free explanations in English or Nigerian Pidgin. No medical degree required — just ask your question naturally.',
  },
];

const STEPS = [
  {
    step: '01',
    title: 'Ask Your Question',
    desc: 'Type any question about pregnancy, antenatal care, childbirth, newborn health, nutrition, or family planning.',
  },
  {
    step: '02',
    title: 'AI Searches Guidelines',
    desc: 'The system searches over 2,400 indexed passages from authoritative health guidelines to find the most relevant information.',
  },
  {
    step: '03',
    title: 'Receive a Safe, Cited Answer',
    desc: 'A vetted response is returned with numbered source citations so you can see exactly where each piece of information came from.',
  },
];

export default function HomePage() {
  return (
    <div className="page">
      <Navbar />

      <main>
        {/* ---- Hero ---- */}
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-badge">Nigeria &middot; WHO &amp; FMOH Guidelines</div>
            <h1 className="hero-title">
              Trusted Maternal Health<br />Guidance, Any Time
            </h1>
            <p className="hero-subtitle">
              AI-powered answers to your pregnancy, childbirth, and newborn health
              questions — grounded in authoritative guidelines and available 24/7.
            </p>
            <div className="hero-actions">
              <Link to="/chat" className="btn btn--white btn--lg">
                Start a Conversation
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <Link to="/faq" className="btn btn--ghost btn--lg">Learn More</Link>
            </div>
            <p className="hero-disclaimer">
              For life-threatening emergencies, call <strong>112</strong> immediately.
            </p>
          </div>
        </section>

        {/* ---- Features ---- */}
        <section className="section features-section">
          <div className="container">
            <div className="section-header">
              <h2 className="section-title">Why Use This Assistant?</h2>
              <p className="section-subtitle">
                Designed for pregnant women, new mothers, caregivers, and community
                health workers across Nigeria.
              </p>
            </div>
            <div className="features-grid">
              {FEATURES.map(f => (
                <div key={f.title} className="feature-card">
                  <span className="feature-icon" aria-hidden="true">{f.icon}</span>
                  <h3 className="feature-title">{f.title}</h3>
                  <p className="feature-desc">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---- How it works ---- */}
        <section className="section how-section">
          <div className="container">
            <div className="section-header">
              <h2 className="section-title">How It Works</h2>
              <p className="section-subtitle">
                From your question to a safe, referenced answer in seconds.
              </p>
            </div>
            <div className="steps-grid">
              {STEPS.map(s => (
                <div key={s.step} className="step-card">
                  <div className="step-number" aria-hidden="true">{s.step}</div>
                  <h3 className="step-title">{s.title}</h3>
                  <p className="step-desc">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---- CTA Banner ---- */}
        <section className="cta-banner">
          <div className="container">
            <h2 className="cta-title">Ready to get maternal health information?</h2>
            <p className="cta-subtitle">
              Ask about antenatal care, danger signs during pregnancy, nutrition,
              immunisation, or anything else — right now.
            </p>
            <Link to="/chat" className="btn btn--white btn--lg">
              Open the Chat Assistant
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
