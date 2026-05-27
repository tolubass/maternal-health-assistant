import MessageList from './MessageList';
import ChatInput from './ChatInput';

function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="error-banner" role="alert">
      <span className="error-icon" aria-hidden="true">⚠️</span>
      <span className="error-text">{message}</span>
      <button
        type="button"
        className="error-dismiss"
        onClick={onDismiss}
        aria-label="Dismiss error"
      >
        ✕
      </button>
    </div>
  );
}

export default function ChatWindow({
  messages,
  isLoading,
  error,
  onSend,
  onDismissError,
}) {
  return (
    <div className="chat-window">
      {error && (
        <ErrorBanner message={error} onDismiss={onDismissError} />
      )}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        onExampleClick={onSend}
      />
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}
