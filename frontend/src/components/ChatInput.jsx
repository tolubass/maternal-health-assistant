import { useState, useRef, useEffect } from 'react';

const MAX_LENGTH = 2000;

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Auto-grow the textarea up to 5 lines, then scroll
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  }, [text]);

  function handleKeyDown(e) {
    // Submit on Enter (without Shift); Shift+Enter inserts a newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  const remaining = MAX_LENGTH - text.length;
  const overLimit = remaining < 0;

  return (
    <form
      className="chat-input-form"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      aria-label="Chat input"
    >
      <div className={`chat-input-wrapper ${overLimit ? 'chat-input-wrapper--error' : ''}`}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a health question…"
          disabled={disabled}
          rows={1}
          maxLength={MAX_LENGTH + 1}
          aria-label="Your question"
          aria-describedby="char-counter"
        />
        <button
          type="submit"
          className="send-btn"
          disabled={disabled || !text.trim() || overLimit}
          aria-label="Send message"
        >
          {disabled ? (
            <span className="send-spinner" aria-hidden="true" />
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          )}
        </button>
      </div>

      <div className="input-meta">
        <span className="input-hint">Shift + Enter for new line</span>
        <span
          id="char-counter"
          className={`char-counter ${remaining < 100 ? 'char-counter--warn' : ''} ${overLimit ? 'char-counter--error' : ''}`}
          aria-live="polite"
        >
          {remaining < 200 ? `${remaining} left` : ''}
        </span>
      </div>
    </form>
  );
}
