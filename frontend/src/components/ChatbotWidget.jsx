import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, RotateCcw, Sparkles } from 'lucide-react';
import { sendChatMessage } from '../api';

const QUICK_PROMPTS = [
  'How much does a full-time cook cost in Mumbai?',
  'What background checks do drivers undergo?',
  'What shifts are available for security guards?',
  'What is your replacement guarantee policy?',
];

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello! 👋 Welcome to HomeDesk. I can answer questions about our verified cook, driver, and security guard services, estimated pricing, and the booking process. How can I help you today?',
    },
  ]);
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend) => {
    const text = (textToSend || inputVal).trim();
    if (!text || isLoading) return;

    const newMsgs = [...messages, { role: 'user', text }];
    setMessages(newMsgs);
    setInputVal('');
    setIsLoading(true);

    try {
      const reply = await sendChatMessage(text);
      setMessages([...newMsgs, { role: 'assistant', text: reply }]);
    } catch (err) {
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: '⚠️ I encountered an issue connecting to the AI assistant. Please ensure your backend is running or check back shortly.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        role: 'assistant',
        text: 'Chat history cleared. How else can I assist your household requirements?',
      },
    ]);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen ? (
        /* Floating Launcher Bubble */
        <button
          onClick={() => setIsOpen(true)}
          className="bg-[#E8A33D] hover:bg-[#C77F1F] text-white p-3.5 rounded-full shadow-xl hover:shadow-2xl transition-all duration-200 flex items-center gap-2.5 font-medium text-xs cursor-pointer group hover:scale-105"
        >
          <div className="relative">
            <MessageSquare size={20} />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#1F7A5C] rounded-full border-2 border-[#E8A33D]" />
          </div>
          <span className="pr-1">AI Assistant</span>
        </button>
      ) : (
        /* Floating Chat Window Card */
        <div className="bg-white border border-[#D9DDE2] rounded-2xl w-[360px] sm:w-[400px] h-[520px] shadow-2xl flex flex-col overflow-hidden animate-float-in">
          {/* Chat Window Header */}
          <div className="bg-[#16243F] text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#E8A33D]/20 text-[#E8A33D] flex items-center justify-center">
                <Bot size={18} />
              </div>
              <div>
                <div className="text-xs font-bold leading-tight flex items-center gap-1.5">
                  <span>HomeDesk Assistant</span>
                  <span className="w-2 h-2 rounded-full bg-[#1F7A5C]" />
                </div>
                <div className="text-[10px] text-[#D9DDE2]/70">
                  Cloud AI &middot; Service Guidance
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1 text-[#D9DDE2]">
              <button
                onClick={handleReset}
                title="Restart chat"
                className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors"
              >
                <RotateCcw size={14} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#F5F6F3]">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] text-xs rounded-2xl p-3 leading-relaxed shadow-sm whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-[#E8A33D] text-white rounded-br-none'
                      : 'bg-white border border-[#D9DDE2] text-[#16243F] rounded-bl-none'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-[#D9DDE2] rounded-2xl rounded-bl-none p-3 text-xs text-[#5B6573] flex items-center gap-2 shadow-sm">
                  <Sparkles size={14} className="text-[#C77F1F] animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}

            {/* Quick Prompts on initial conversation */}
            {messages.length === 1 && !isLoading && (
              <div className="pt-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#5B6573] mb-1.5">
                  Frequently Asked:
                </div>
                <div className="space-y-1.5">
                  {QUICK_PROMPTS.map((prompt, pIdx) => (
                    <button
                      key={pIdx}
                      onClick={() => handleSend(prompt)}
                      className="w-full text-left text-[11px] bg-white hover:bg-[#E8A33D]/10 border border-[#D9DDE2] hover:border-[#E8A33D] text-[#16243F] p-2 rounded-lg transition-all"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-3 bg-white border-t border-[#D9DDE2] flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Ask anything about our services..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              className="flex-1 text-xs px-3 py-2 border border-[#D9DDE2] rounded-xl focus:outline-none focus:border-[#E8A33D]"
            />
            <button
              type="submit"
              disabled={!inputVal.trim() || isLoading}
              className="w-8 h-8 rounded-xl bg-[#E8A33D] hover:bg-[#C77F1F] text-white flex items-center justify-center transition-colors disabled:opacity-40 cursor-pointer shrink-0"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
