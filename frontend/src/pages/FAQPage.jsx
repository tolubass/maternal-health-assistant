import { useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const FAQS = [
  {
    q: 'What is antenatal care (ANC) and why is it important?',
    a: 'Antenatal care (ANC) is the healthcare provided to a pregnant woman from conception until labour begins. It allows health workers to monitor the health of both mother and baby, detect complications early, administer important supplements (iron and folic acid), give vaccines, and provide health education. The Nigerian Federal Ministry of Health recommends at least 8 ANC contacts during pregnancy.',
  },
  {
    q: 'How many antenatal visits should I have during pregnancy?',
    a: 'WHO and the Nigerian FMOH recommend a minimum of 8 antenatal care contacts: the first before 12 weeks, then at 20, 26, 30, 34, 36, 38, and 40 weeks. Each visit includes blood pressure and weight checks, urine tests, fetal heartbeat monitoring, and screening for complications such as anaemia and pre-eclampsia.',
  },
  {
    q: 'What are the danger signs during pregnancy I should never ignore?',
    a: 'Seek immediate medical care if you experience: heavy vaginal bleeding, severe headache or blurred vision, sudden swelling of the face, hands, or feet, high fever, severe abdominal pain, baby not moving, convulsions or fits, difficulty breathing, or foul-smelling vaginal discharge. Call emergency services (112) or go to the nearest health facility immediately — do not wait.',
  },
  {
    q: 'What should a pregnant woman eat for good nutrition?',
    a: 'A pregnant woman needs a balanced diet rich in iron (beans, dark leafy vegetables, red meat), folic acid (leafy greens, fortified foods), calcium (milk, fish with edible bones, dairy), protein (eggs, fish, legumes, groundnuts), and a variety of fruits and vegetables for vitamins and minerals. Avoid alcohol, raw or undercooked meat, and excessive caffeine. Take iron and folic acid supplements as prescribed by your health worker at every ANC visit.',
  },
  {
    q: 'What vaccines does a pregnant woman need in Nigeria?',
    a: 'In Nigeria, pregnant women should receive Tetanus Toxoid (TT) vaccine to protect the newborn against neonatal tetanus — a minimum of 2 doses during the first pregnancy, with booster doses in subsequent pregnancies. Additional vaccines (such as influenza) may be recommended by your health worker depending on your circumstances. The NPHCDA immunisation schedule provides the full national guidance.',
  },
  {
    q: 'How can I prepare for a safe delivery?',
    a: 'Prepare a birth plan with your health worker. Choose a health facility for delivery well before your due date. Arrange transport in advance. Pack a delivery bag with clean cloths, baby clothing, identification documents, and your antenatal card. Identify a blood donor if needed. Know the warning signs of labour starting — regular contractions, water breaking, or heavy show (blood-stained mucus). If in doubt, go to the health facility.',
  },
  {
    q: 'What is postpartum care and why is it important?',
    a: 'Postpartum care is the healthcare provided to a mother and newborn after delivery. The first 6 weeks are critical. Key checks include: monitoring for heavy bleeding and infection in the mother, checking blood pressure, ensuring the newborn feeds well and has a normal temperature, screening for postpartum depression, and providing family planning counselling. The first postnatal visit should happen within 24 hours of delivery at a health facility.',
  },
  {
    q: 'How do I know if my newborn is healthy?',
    a: 'A healthy newborn cries immediately at birth, feeds well (at least 8–12 times per day for breastfed babies), maintains a normal temperature (36.5–37.5°C), passes urine within the first 24 hours, and gains weight steadily. Seek immediate care if your baby has a high fever (above 38°C), difficulty breathing, persistent vomiting, refuses to feed, appears very yellow (jaundice), or is unusually floppy or unresponsive.',
  },
  {
    q: 'What are the benefits of exclusive breastfeeding?',
    a: 'WHO and UNICEF recommend exclusive breastfeeding — breast milk only, with no water, formula, or other foods — for the first 6 months of life. Benefits for the baby include optimal nutrition, protection against infections and diarrhoea, reduced risk of obesity and chronic diseases, and stronger mother-child bonding. Benefits for the mother include faster post-delivery recovery, reduced risk of breast and ovarian cancer, and natural birth spacing.',
  },
  {
    q: 'How can I prevent malaria during pregnancy?',
    a: 'Malaria in pregnancy can cause severe anaemia, low birth weight, and premature birth. Prevention includes: Intermittent Preventive Treatment in Pregnancy (IPTp) — sulfadoxine-pyrimethamine tablets given at each ANC visit from the second trimester onwards; sleeping every night under an insecticide-treated bed net (ITN); wearing long-sleeved clothing in the evening; and seeking prompt treatment if fever develops. Do not self-medicate — consult a health worker.',
  },
  {
    q: 'Can I use the chat assistant in Nigerian Pidgin?',
    a: 'Yes. The assistant understands Nigerian Pidgin English as well as standard English. You can ask questions in whichever way feels natural — for example, "How many times I suppose go hospital for pregnancy?" is understood just as well as the formal equivalent.',
  },
  {
    q: 'Is the information provided medically accurate?',
    a: 'All answers are grounded in indexed passages from WHO guidelines, Nigerian Federal Ministry of Health protocols, NPHCDA documents, UNICEF maternal health resources, and NCDC guidance — over 2,400 verified passages in total. Every response includes numbered source citations so you can see exactly where the information came from. This assistant does not replace a qualified health worker; always consult a healthcare professional for personal medical decisions.',
  },
  {
    q: 'What should I do if I am having a medical emergency?',
    a: 'Do NOT wait for a chat response. Call the National Emergency line at 112 immediately, or go to the nearest health facility. The assistant will always direct you to seek emergency care when life-threatening symptoms are detected — heavy bleeding, convulsions, loss of consciousness, a newborn not breathing, or a baby with high fever. It is not a substitute for emergency services.',
  },
];

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`faq-item${open ? ' faq-item--open' : ''}`}>
      <button
        className="faq-question"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
      >
        <span>{q}</span>
        <svg
          className="faq-chevron"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && <div className="faq-answer">{a}</div>}
    </div>
  );
}

export default function FAQPage() {
  return (
    <div className="page">
      <Navbar />

      <main>
        {/* ---- Page hero ---- */}
        <section className="page-hero">
          <div className="container">
            <h1 className="page-hero-title">Frequently Asked Questions</h1>
            <p className="page-hero-subtitle">
              Common questions about maternal and child health in Nigeria — answered
              from authoritative guidelines.
            </p>
          </div>
        </section>

        {/* ---- FAQ list ---- */}
        <section className="section">
          <div className="container container--narrow">
            <div className="faq-list">
              {FAQS.map(f => (
                <FAQItem key={f.q} q={f.q} a={f.a} />
              ))}
            </div>

            <div className="faq-cta">
              <p>Still have a question that isn&apos;t covered here?</p>
              <Link to="/chat" className="btn btn--primary btn--md">
                Ask the Chat Assistant
              </Link>
            </div>
          </div>
        </section>

        {/* ---- Contact ---- */}
        <section className="contact-section">
          <div className="container container--narrow">
            <h2 className="contact-title">Contact Us</h2>
            <p className="contact-subtitle">
              Have feedback, want to report an issue, or need to get in touch?
              We&apos;d love to hear from you.
            </p>
            <div className="contact-cards">
              <div className="contact-card">
                <span className="contact-icon" aria-hidden="true">📍</span>
                <div>
                  <div className="contact-label">Location</div>
                  <div className="contact-value">Abuja, Nigeria</div>
                </div>
              </div>
              <div className="contact-card">
                <span className="contact-icon" aria-hidden="true">📞</span>
                <div>
                  <div className="contact-label">Phone</div>
                  <a href="tel:+2349064369708" className="contact-value contact-link">
                    +234 906 436 9708
                  </a>
                </div>
              </div>
              <div className="contact-card">
                <span className="contact-icon" aria-hidden="true">✉️</span>
                <div>
                  <div className="contact-label">Email</div>
                  <a
                    href="mailto:stratnalytiq@gmail.com"
                    className="contact-value contact-link"
                  >
                    stratnalytiq@gmail.com
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
