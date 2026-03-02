
import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { getGeminiInsight } from '../services/geminiService';
import { contracts, activities, financials } from '../data/mockData';

const AIChat: React.FC = () => {
  const [messages, setMessages] = useState<{role: 'ai' | 'user', content: string}[]>([
    { role: 'ai', content: 'Olá! Sou seu Assistente Executivo IA. Analiso todos os dados da BOMTEMPO em tempo real. Como posso ajudar com insights estratégicos hoje?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    const dataContext = { contracts, activities, financials };
    const aiResponse = await getGeminiInsight(userMsg, dataContext);

    setMessages(prev => [...prev, { role: 'ai', content: aiResponse }]);
    setIsLoading(false);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col bg-[#0D2A23] rounded-3xl border border-[#1A3A30] overflow-hidden page-transition">
      <div className="p-6 border-b border-[#1A3A30] bg-gradient-to-r from-[#0B5B3E]/30 to-transparent flex items-center justify-between">
        <div className="flex items-center">
          <div className="w-10 h-10 rounded-full bg-[#C98B2A] flex items-center justify-center text-[#0A1F1A] shadow-lg shadow-[#C98B2A]/20">
            <Sparkles size={20} />
          </div>
          <div className="ml-4">
            <h3 className="text-white font-black">BOMTEMPO Intelligence</h3>
            <span className="text-[10px] text-[#4ADE80] font-bold uppercase tracking-widest">IA Conectada em Tempo Real</span>
          </div>
        </div>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth"
      >
        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 ${
                msg.role === 'user' ? 'bg-[#0B5B3E] ml-3' : 'bg-[#C98B2A] mr-3'
              }`}>
                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} className="text-[#0A1F1A]" />}
              </div>
              <div className={`p-5 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user' 
                ? 'bg-[#C98B2A] text-[#0A1F1A] font-bold rounded-tr-none' 
                : 'bg-[#1A3A30] text-white border border-[#C98B2A]/20 rounded-tl-none shadow-xl'
              }`}>
                {msg.content}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex flex-row items-center space-x-2 bg-[#1A3A30] px-4 py-2 rounded-full border border-[#C98B2A]/20">
              <div className="w-1.5 h-1.5 bg-[#C98B2A] rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-[#C98B2A] rounded-full animate-bounce delay-75"></div>
              <div className="w-1.5 h-1.5 bg-[#C98B2A] rounded-full animate-bounce delay-150"></div>
            </div>
          </div>
        )}
      </div>

      <div className="p-6 bg-[#0A1F1A]/50 border-t border-[#1A3A30]">
        <div className="relative">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Pergunte sobre rentabilidade, prazos críticos ou performance..."
            className="w-full bg-[#1A3A30] border border-[#1A3A30] focus:border-[#C98B2A] text-white rounded-2xl px-6 py-4 outline-none transition-all pr-16 shadow-inner"
          />
          <button 
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="absolute right-2 top-2 bottom-2 w-12 bg-[#C98B2A] text-[#0A1F1A] rounded-xl flex items-center justify-center hover:bg-[#E0A63B] transition-colors disabled:opacity-50"
          >
            <Send size={20} />
          </button>
        </div>
        <p className="text-center text-[10px] text-[#A0A0A0] mt-4 font-bold uppercase tracking-widest">
          Insights gerados por Google Gemini • Utilize para apoio à decisão estratégica
        </p>
      </div>
    </div>
  );
};

export default AIChat;
