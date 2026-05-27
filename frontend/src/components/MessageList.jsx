import { useEffect, useRef } from 'react';
import Message from './Message';
import { EXAMPLE_QUESTIONS } from '../hooks/useChat';

function TypingIndicator() {
  return (
    <div className="msg msg--assistant" aria-label="Assistant is typing">
      <span className="msg-avatar" aria-hidden="true">🩺</span>
      <div className="msg-body">
        <div className="typing-indicator">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onExampleClick }) {
  return (
    <div className="welcome">
      <div className="welcome-icon" aria-hidden="true">🤰</div>
      <h2 className="welcome-title">Maternal Health Assistant</h2>
      <p className="welcome-subtitle">
        Grounded in WHO and Nigerian FMOH guidelines. Ask about pregnancy,
        antenatal care, childbirth, newborn health, nutrition, and more.
      </p>
      <ul className="example-list" aria-label="Example questions">
        {EXAMPLE_QUESTIONS.map((q) => (
          <li key={q}>
            <button
              type="button"
              className="example-btn"
              onClick={() => onExampleClick(q)}
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function MessageList({ messages, isLoading, onExampleClick }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="message-list message-list--empty">
        <WelcomeScreen onExampleClick={onExampleClick} />
      </div>
    );
  }

  return (
    <div className="message-list" role="list" aria-label="Conversation">
      {messages.map((msg) => (
        <div key={msg.id} role="listitem">
          <Message message={msg} />
        </div>
      ))}
      {isLoading && <TypingIndicator />}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
}
