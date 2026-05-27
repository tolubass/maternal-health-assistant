import { useState, useCallback, useRef, useEffect } from 'react';
import { sendMessage } from '../services/api';

let _nextId = 1;
const uid = () => _nextId++;

export const EXAMPLE_QUESTIONS = [
  'What are the danger signs during pregnancy?',
  'How many antenatal visits should I have?',
  'What should a pregnant woman eat for good nutrition?',
  'How do I know if my newborn is healthy?',
  'What is postpartum care and why is it important?',
];

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const messagesRef = useRef(messages);
  useEffect(() => { messagesRef.current = messages; });

  const submit = useCallback(async (question) => {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    const history = messagesRef.current
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }));

    const userMsg = { id: uid(), role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const data = await sendMessage(trimmed, history);
      const isEmergency =
        data.answer.includes('🚨') ||
        data.answer.toLowerCase().includes('medical emergency');

      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: data.answer,
          citations: data.citations ?? [],
          isEmergency,
        },
      ]);
    } catch (err) {
      setError(err.message || 'Could not reach the server. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { messages, isLoading, error, submit, clearChat, clearError };
}
