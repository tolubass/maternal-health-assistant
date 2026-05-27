import { useEffect, useState } from 'react';
import { useChat } from '../hooks/useChat';
import { fetchHealth } from '../services/api';
import ChatWindow from '../components/ChatWindow';
import Navbar from '../components/Navbar';

function StatusDot({ healthy }) {
  return (
    <span
      className={`status-dot ${healthy ? 'status-dot--ok' : 'status-dot--err'}`}
      title={healthy ? 'Service online' : 'Service unreachable'}
      aria-label={healthy ? 'Service online' : 'Service unreachable'}
    />
  );
}

export default function ChatPage() {
  const { messages, isLoading, error, submit, clearChat, clearError } = useChat();
  const [healthy, setHealthy] = useState(null);

  useEffect(() => {
    fetchHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <div className="chat-page">
      <Navbar />

      <div className="chat-page-bar-wrap">
        <div className="chat-page-bar">
          <span className="chat-page-title">Ask a maternal health question</span>
          <div className="chat-page-actions">
            {messages.length > 0 && (
              <button
                type="button"
                className="new-chat-btn"
                onClick={clearChat}
                aria-label="Start a new conversation"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                </svg>
                New chat
              </button>
            )}
            {healthy !== null && <StatusDot healthy={healthy} />}
          </div>
        </div>
      </div>

      <main className="chat-page-main">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          error={error}
          onSend={submit}
          onDismissError={clearError}
        />
      </main>
    </div>
  );
}
