
import React from 'react';
import { 
  LayoutDashboard, 
  Briefcase, 
  Construction, 
  Wallet, 
  Zap, 
  MessageSquare, 
  BarChart3, 
  TrendingUp,
  Menu,
  X
} from 'lucide-react';
import { Page } from '../types';

interface SidebarProps {
  activePage: Page;
  onPageChange: (page: Page) => void;
  isCollapsed: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, onPageChange, isCollapsed, onToggle }) => {
  const menuItems = [
    { id: Page.OVERVIEW, icon: LayoutDashboard, label: 'VISÃO GERAL' },
    { id: Page.PROJECTS, icon: Briefcase, label: 'PROJETOS' },
    { id: Page.CONSTRUCTION, icon: Construction, label: 'OBRAS' },
    { id: Page.FINANCE, icon: Wallet, label: 'FINANCEIRO' },
    { id: Page.OM, icon: Zap, label: 'O&M' },
    { id: Page.ANALYTICS, icon: BarChart3, label: 'ANALYTICS' },
    { id: Page.FORECASTS, icon: TrendingUp, label: 'PREVISÕES ML' },
    { id: Page.AI_CHAT, icon: MessageSquare, label: 'CHAT IA' },
  ];

  return (
    <aside 
      className={`glass-panel border-r-0 border-r border-[#ffffff0a] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col h-[calc(100vh-2rem)] my-4 ml-4 rounded-2xl sticky top-4 ${isCollapsed ? 'w-20' : 'w-72'}`}
    >
      {/* Brand Header */}
      <div className="p-8 flex items-center justify-between">
        {!isCollapsed && (
          <div className="flex flex-col animate-enter">
            <span className="text-[#C98B2A] font-bold text-2xl tracking-tight font-tech">BOMTEMPO</span>
            <div className="flex items-center gap-2">
               <div className="h-[1px] w-4 bg-[#2A9D8F]"></div>
               <span className="text-[#889999] text-[9px] uppercase font-bold tracking-[0.3em]">Engenharia</span>
            </div>
          </div>
        )}
        <button 
          onClick={onToggle}
          className="p-2 rounded-lg text-[#889999] hover:text-[#C98B2A] transition-colors"
        >
          {isCollapsed ? <Menu size={20} /> : <div className="p-1 border border-[#ffffff1a] rounded"><X size={14} /></div>}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-4 space-y-1">
        {menuItems.map((item, idx) => {
          const isActive = activePage === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
              style={{ animationDelay: `${idx * 50}ms` }}
              className={`animate-enter w-full flex items-center p-3 rounded-lg transition-all duration-300 group relative overflow-hidden ${
                isActive 
                ? 'bg-[#C98B2A]/10 text-[#C98B2A] border border-[#C98B2A]/30' 
                : 'text-[#889999] hover:text-[#E0E0E0] hover:bg-[#ffffff05] border border-transparent'
              }`}
            >
              {isActive && (
                 <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#C98B2A] shadow-[0_0_10px_#C98B2A]"></div>
              )}
              
              <Icon size={20} strokeWidth={1.5} className={isActive ? 'text-[#C98B2A]' : 'group-hover:text-[#E0E0E0] transition-colors'} />
              
              {!isCollapsed && (
                <span className={`ml-4 text-xs font-bold tracking-widest font-tech ${isActive ? 'text-[#E0E0E0]' : ''}`}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* User Status */}
      <div className="p-6">
        <div className={`p-4 rounded-xl bg-[#030504]/50 border border-[#ffffff0a] flex items-center ${isCollapsed ? 'justify-center' : 'gap-4'}`}>
          <div className="relative">
             <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#2A9D8F] to-[#084932] flex items-center justify-center text-white font-bold font-tech shadow-lg">
               JD
             </div>
             <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-[#C98B2A] border-2 border-[#030504] rounded-full"></div>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-bold text-[#E0E0E0] truncate">João Diretor</span>
              <span className="text-[9px] text-[#2A9D8F] uppercase font-bold tracking-wider">C-Level Access</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
