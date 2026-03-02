
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import { Page } from './types';
import Overview from './views/Overview';
import AIChat from './views/AIChat';
import Projects from './views/Projects';
import Construction from './views/Construction';
import Finance from './views/Finance';
import OM from './views/OM';
import Analytics from './views/Analytics';
import Forecasts from './views/Forecasts'; 
import { Menu, X } from 'lucide-react';

const App: React.FC = () => {
  const [activePage, setActivePage] = useState<Page>(Page.OVERVIEW);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const renderPage = () => {
    switch (activePage) {
      case Page.OVERVIEW:
        return <Overview />;
      case Page.PROJECTS:
        return <Projects />;
      case Page.CONSTRUCTION:
        return <Construction />;
      case Page.FINANCE:
        return <Finance />;
      case Page.OM:
        return <OM />;
      case Page.ANALYTICS:
        return <Analytics />;
      case Page.FORECASTS: 
        return <Forecasts />;
      case Page.AI_CHAT:
        return <AIChat />;
      default:
        return (
          <div className="flex flex-col items-center justify-center h-[60vh] text-center p-12 glass-panel rounded-3xl">
            <h2 className="text-3xl font-tech font-bold text-[#C98B2A] mb-4">SYSTEM MODULE OFFLINE</h2>
            <p className="text-[#889999] max-w-md">This sector is currently under development. Please utilize the Command Center or AI Agent for available data.</p>
          </div>
        );
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-[#030504]/90 backdrop-blur-sm z-[60] lg:hidden" 
          onClick={() => setMobileMenuOpen(false)}
        ></div>
      )}

      {/* Main Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-[70] transform lg:relative lg:translate-x-0 transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar 
          activePage={activePage} 
          onPageChange={(p) => {
            setActivePage(p);
            setMobileMenuOpen(false);
          }} 
          isCollapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Content Wrapper */}
      <main className="flex-1 min-w-0 overflow-x-hidden p-4 lg:p-6 lg:pr-8">
        <div className="max-w-[1600px] mx-auto">
          {/* Mobile Header Bar */}
          <div className="flex items-center justify-between mb-8 lg:hidden glass-panel p-4 rounded-xl">
             <div className="flex flex-col">
              <span className="text-[#C98B2A] font-tech font-bold text-xl tracking-tighter">BOMTEMPO</span>
              <span className="text-[#889999] text-[9px] uppercase font-bold tracking-[0.2em]">Engenharia</span>
            </div>
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 bg-[#ffffff05] rounded-lg text-[#C98B2A] border border-[#ffffff0a]"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>

          {renderPage()}
        </div>
      </main>
    </div>
  );
};

export default App;
