
import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KPICardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  delta?: string;
  isPositive?: boolean;
  delay?: number;
}

const KPICard: React.FC<KPICardProps> = ({ label, value, icon: Icon, delta, isPositive = true, delay = 0 }) => {
  return (
    <div 
      style={{ animationDelay: `${delay}ms` }}
      className="glass-panel p-6 rounded-2xl relative group hover:border-[#C98B2A]/50 transition-all duration-500 animate-enter"
    >
      {/* Hover Glow Effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#C98B2A]/0 to-[#C98B2A]/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl pointer-events-none"></div>
      
      <div className="flex justify-between items-start mb-4">
        <div className="p-3 bg-[#ffffff05] rounded-xl border border-[#ffffff0a] text-[#C98B2A] group-hover:scale-110 transition-transform duration-300">
          <Icon size={24} strokeWidth={1.5} />
        </div>
        
        {delta && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold tracking-wider border ${
            isPositive 
            ? 'bg-[#2A9D8F]/10 border-[#2A9D8F]/20 text-[#2A9D8F]' 
            : 'bg-[#EF4444]/10 border-[#EF4444]/20 text-[#EF4444]'
          }`}>
             {isPositive ? '▲' : '▼'} {delta}
          </div>
        )}
      </div>
      
      <div className="space-y-1 relative z-10">
        <h3 className="text-[#889999] text-[10px] uppercase font-bold tracking-[0.2em]">{label}</h3>
        <p className="text-3xl text-[#E0E0E0] font-tech font-semibold tracking-tight">{value}</p>
      </div>

      {/* Decorative Corner */}
      <div className="absolute top-0 right-0 p-2 opacity-30">
        <svg width="20" height="20" viewBox="0 0 20 20">
           <path d="M0,0 L20,0 L20,20" fill="none" stroke="#C98B2A" strokeWidth="1" />
        </svg>
      </div>
    </div>
  );
};

export default KPICard;
