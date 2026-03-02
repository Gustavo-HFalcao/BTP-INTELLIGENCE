
import React, { useState } from 'react';
import { Search, MapPin, Calendar, ArrowRight, X, Clock, AlertCircle } from 'lucide-react';
import { contracts, activities } from '../data/mockData';
import { ContractRecord } from '../types';

const Projects: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProject, setSelectedProject] = useState<ContractRecord | null>(null);

  const filtered = contracts.filter(c => 
    c.contrato.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.cliente.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-enter">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-tech font-bold text-white uppercase">Gestão de Projetos</h2>
          <p className="text-[#889999] text-sm">Portfolio e Cronogramas Detalhados</p>
        </div>
        
        {!selectedProject && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#889999]" size={16} />
            <input 
              type="text" 
              placeholder="Buscar contrato..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-[#ffffff05] border border-[#ffffff0a] text-white pl-10 pr-4 py-2 rounded-xl outline-none focus:border-[#C98B2A] transition-all w-64 text-sm font-mono"
            />
          </div>
        )}
      </div>

      {selectedProject ? (
        <div className="animate-enter">
          {/* Detail View Header */}
          <div className="flex justify-between items-center mb-6">
            <button 
              onClick={() => setSelectedProject(null)}
              className="text-[#C98B2A] flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <ArrowRight className="rotate-180" size={20} /> Voltar para Lista
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Project Info Panel */}
            <div className="glass-panel p-8 rounded-3xl h-fit">
              <h3 className="text-2xl font-tech font-bold text-white mb-6">{selectedProject.cliente}</h3>
              <div className="space-y-6">
                <div className="flex justify-between items-center p-4 bg-[#ffffff03] rounded-xl border border-[#ffffff05]">
                  <span className="text-[#889999] text-xs uppercase tracking-widest">Contrato</span>
                  <span className="text-[#C98B2A] font-mono font-bold">{selectedProject.contrato}</span>
                </div>
                <div className="flex justify-between items-center p-4 bg-[#ffffff03] rounded-xl border border-[#ffffff05]">
                   <span className="text-[#889999] text-xs uppercase tracking-widest">Status</span>
                   <span className={`px-2 py-1 rounded text-[10px] uppercase font-bold ${
                     selectedProject.status === 'Em Execução' ? 'bg-[#2A9D8F]/20 text-[#2A9D8F]' : 'bg-[#EF4444]/20 text-[#EF4444]'
                   }`}>{selectedProject.status}</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div>
                     <p className="text-[#889999] text-[10px] uppercase">Início</p>
                     <p className="text-white font-mono text-sm">{selectedProject.projetoInicio}</p>
                   </div>
                   <div>
                     <p className="text-[#889999] text-[10px] uppercase">Estimativa</p>
                     <p className="text-white font-mono text-sm">{selectedProject.terminoEstimado}</p>
                   </div>
                </div>
              </div>
            </div>

            {/* Gantt / Timeline Simulation */}
            <div className="lg:col-span-2 glass-panel p-8 rounded-3xl">
               <h3 className="text-xl font-tech font-bold text-white mb-6 flex items-center">
                 <Calendar className="mr-3 text-[#C98B2A]" /> Cronograma de Atividades
               </h3>
               
               <div className="space-y-4">
                 {activities.map((act, idx) => (
                   <div key={idx} className="relative">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-white font-bold">{act.atividade}</span>
                        <span className="text-[#889999]">{act.fase}</span>
                      </div>
                      <div className="h-4 bg-[#ffffff05] rounded-full overflow-hidden flex items-center relative">
                        {/* Progress Bar */}
                        <div 
                          className={`h-full rounded-full transition-all duration-1000 ${
                            act.critico ? 'bg-gradient-to-r from-[#EF4444] to-[#B91C1C]' : 'bg-gradient-to-r from-[#C98B2A] to-[#E0A63B]'
                          }`} 
                          style={{ width: `${act.conclusao}%` }}
                        ></div>
                        <span className="absolute right-2 text-[9px] font-bold text-white mix-blend-difference">{act.conclusao}%</span>
                      </div>
                      {act.critico && (
                        <div className="flex items-center gap-1 mt-1">
                          <AlertCircle size={10} className="text-[#EF4444]" />
                          <span className="text-[9px] text-[#EF4444] uppercase tracking-wider">Caminho Crítico</span>
                        </div>
                      )}
                   </div>
                 ))}
               </div>
            </div>
          </div>
        </div>
      ) : (
        /* List View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((c, i) => (
            <div 
              key={i} 
              onClick={() => setSelectedProject(c)}
              className="glass-panel p-6 rounded-2xl cursor-pointer hover:border-[#C98B2A] transition-all group relative overflow-hidden"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <ArrowRight className="text-[#C98B2A]" />
              </div>

              <div className="mb-4">
                <span className="text-[#C98B2A] font-tech font-bold text-lg">{c.contrato}</span>
                <h3 className="text-white font-bold text-xl mt-1">{c.cliente}</h3>
              </div>
              
              <div className="space-y-3 mb-6">
                 <div className="flex items-center text-[#889999] text-sm">
                    <MapPin size={14} className="mr-2" /> {c.localizacao}
                 </div>
                 <div className="flex items-center text-[#889999] text-sm">
                    <Clock size={14} className="mr-2" /> {c.prazoContratual}
                 </div>
              </div>

              <div className="mt-4 pt-4 border-t border-[#ffffff0a]">
                <div className="flex justify-between items-end mb-2">
                  <span className="text-[10px] text-[#889999] uppercase font-bold">Progresso Global</span>
                  <span className="text-white font-mono font-bold">{c.progress}%</span>
                </div>
                <div className="h-1 bg-[#ffffff0a] rounded-full overflow-hidden">
                  <div className="h-full bg-[#2A9D8F]" style={{ width: `${c.progress}%` }}></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Projects;
