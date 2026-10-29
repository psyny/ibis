import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';

export type MessageType = 'error' | 'success' | 'info';

interface Message {
  id: number;
  type: MessageType;
  content: string;
}

interface MessageContextType {
  showMessage: (type: MessageType, content: string) => void;
}

const MessageContext = createContext<MessageContextType | undefined>(undefined);

export function MessageProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<Message | null>(null);

  const showMessage = useCallback((type: MessageType, content: string) => {
    setMessage({ id: Date.now(), type, content });
  }, []);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), message.type === 'error' ? 6000 : 3500);
    return () => clearTimeout(timer);
  }, [message]);

  return (
    <MessageContext.Provider value={{ showMessage }}>
      {children}
      {message && (
        <div className={`toast toast--${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>
          <span>{message.content}</span>
          <button className="toast__close" onClick={() => setMessage(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}
    </MessageContext.Provider>
  );
}

export function useMessage() {
  const context = useContext(MessageContext);
  if (!context) throw new Error('useMessage must be used within MessageProvider');
  return context.showMessage;
}
